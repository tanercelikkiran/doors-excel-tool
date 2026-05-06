# Technical Specification: DOORS-Excel Bidirectional Conversion Tool

This document defines the architectural foundation and technology stack for the DOORS-Excel conversion tool, ensuring robustness, maintainability, and security.

## 1. Architectural Principles
- **Layered Architecture**: Strict separation between the Presentation (PySide6/Typer), Domain (Transformation Logic), and Data/Infrastructure (DOORS/Excel Gateways) layers.
- **Resilient Integration**: Implementation of retry patterns and circuit breakers for the inherently unstable Windows COM interface.
- **Defensive DXL Execution**: All DXL logic is treated as potentially dangerous; strict templating and sanitization are mandatory to prevent injection [REQ-SEC-702].
- **Batch-Oriented Processing**: To handle modules up to 50k objects [REQ-PER-503], the system uses a windowed batching strategy for DXL execution and Excel I/O [REQ-SYS-304].

## 2. Core Language & Environment
- **Python 3.10+**: Core language for its rich data science and Windows integration libraries.
- **Poetry**: Dependency management and packaging.
- **qasync**: Integration layer that allows the `asyncio` event loop to run inside the `PySide6` (Qt) event loop. 
  - **Signaling Mechanism:** Uses custom Qt Signals to emit progress updates from the DXL execution engine to the UI, supporting multi-level tracking (Global progress vs. Batch/Chunk progress) [REQ-SYS-307].
- **SQLite (sqlite3)**: Used as the authoritative data engine for high-performance Dry-Run diff results and as a persistent 'Session History & Rollback' store [REQ-SAF-406]. 
  - **Pure SQL Diffing:** To handle 50,000 object modules with large text fields [REQ-PER-503], the system performs 3-way merge and change detection entirely using SQL queries (JOINs, CTEs) on staging tables, bypassing Pandas memory limits. 
    - **Conflict Identification:** The SQL logic shall specifically flag attributes where `staging_excel.value != staging_doors.value` AND both differ from `staging_baseline.value` as "Attribute Conflicts" [REQ-FUN-207].
  - **Hierarchical Traversal:** The diff engine shall use **Recursive Common Table Expressions (CTEs)** to traverse the DOORS hierarchy in SQLite. This is mandatory for detecting "Indirect Deletions" [REQ-FUN-209.2] by identifying all descendants of objects marked for Purge in Excel.
- **Data Flow**: DOORS/Excel -> SQLite (Staging) -> SQL-Based 3-Way Merge -> SQLite (Diff Results) -> UI (Paginated).
- **Schema Definition**: 
  - `staging_doors`, `staging_excel`, `staging_baseline`: Temporary tables for SQL-based diffing.
  - `session_history`: Stores metadata for all operations.
  - `validation_errors`: Stores row-level issues.
  - `diff_results`: Stores object-level changes.
  - `rollback_snapshots`: Stores pre-update attribute values. For purged objects, data is preserved to allow recreation as new objects, although their original Absolute Numbers cannot be restored [REQ-SAF-406.1].- **pywin32 (win32com.client)**: The low-level COM bridge.
  - **Thread Isolation:** All COM interactions are isolated in a dedicated background thread configured for Single Threaded Apartment (STA).
  - **Message Filtering:** Implements `pythoncom.CoRegisterMessageFilter` to handle `SERVERCALL_RETRYLATER` and `PENDINGMSG_WAITDEFPROCESS`, providing robust handling for high-latency connections [C-6].
  - **Background Keep-Alive:** The COM worker thread implements a watchdog timer that triggers a minimal DXL "ping" if no activity is detected for a defined interval (default 60s). This ensures the DOORS client remains active and prevents session timeouts during long data-processing phases that occur outside the COM bridge (e.g., SQLite diffing or RTF-to-Markdown conversion) [REQ-SYS-308].
  - **Early Binding:** Uses `win32com.client.gencache.EnsureDispatch` to minimize network round-trips for COM method discovery.
- **Tenacity**: Advanced retry library to handle transient COM errors (e.g., `CO_E_SERVER_EXEC_FAILURE`) [REQ-REL-602].
- **Jinja2**: Parametric DXL template engine. Used to generate complex, bulk DXL scripts at runtime. 
  - **DXL Injection Protection**: Implements a custom Jinja2 filter `dxl_value` that rigorously escapes backslashes, double quotes, and newlines. All dynamic data passed to DXL templates MUST use this filter [REQ-SEC-702, REQ-FUN-216].
  - This minimizes COM overhead by executing multiple updates or queries in a single DXL execution block, significantly improving synchronization speed [REQ-SYS-302, REQ-FUN-216].
- **openpyxl**: High-fidelity Excel manipulation (.xlsx and .xlsm), supporting the "Error Feedback" styling required by [REQ-SAF-402] and managing **Sheet-Scoped Hidden Defined Names** for robust module-to-worksheet mapping [REQ-FUN-113.2, REQ-FUN-215.1]. 
  - **Formula Handling**: To ensure data integrity, the tool **must** use the `data_only=True` parameter when loading workbooks. This ensures that the calculated results of Excel formulas (e.g., `="REQ-" & A2`) are read instead of the formula strings themselves, preventing incorrect data from being imported into DOORS.
  - **Metadata Integrity Persistence**: Utilized to write and read cryptographic hashes into Workbook Custom Properties or Hidden Defined Names to satisfy [REQ-FUN-117].
  - This ensures metadata persistence during sheet movements or renaming.
- **pandas**: Used primarily for lightweight I/O and tabular data loading. To prevent `MemoryError` in large modules, all set-based diffing and 3-way merge logic is delegated to the SQLite SQL engine.
- **mistune**: High-performance Markdown parser used to convert Excel GFM text into an Abstract Syntax Tree (AST) for the custom RTF renderer during import.
- **networkx**: Library used for directed graph analysis to detect circular link dependencies during the Dry-Run phase [REQ-FUN-214].
  - **Scale Optimization**: For 50k object modules, the tool uses a dedicated edge-only extraction strategy to build the graph efficiently.

## 3. RTF, OLE & Graph Analysis
- **Link Graph Extraction**: Uses a lightweight DXL template to extract directed edges (Source -> Target) in batches. This avoids the overhead of full attribute extraction for cycle detection.
  - **Batched Buffer Loading:** To optimize extraction for 50k objects, the tool executes the script in chunks (e.g., 5,000 objects), accumulating results into a DXL `Buffer` object before returning data via COM to minimize bridge overhead.
- **Link Parsing Regex**: A named-group regex is used to decompose link commands from Excel: `^(?:(?P<action>DEL):)?\s*(?:\[(?P<id>[^\]]+)\]\s*\(Type:\s*"(?P<type>(?:[^"]|"")*?)",\s*Mod:\s*"(?P<mod>(?:[^"]|"")*?)"\)|(?P<target>doors://\S+|\d+))$`.
- **rtfparse**: Robust RTF-to-Tree parsing to preserve formatting during Markup conversion [REQ-FUN-105.1].
  - **Mapping Strategy**: Custom logic to traverse the RTF tree and emit Markdown syntax for supported control words (e.g., `\b` -> `**`, `\i` -> `*`, `\par` -> `\n`).
- **Markdown-to-RTF Engine (Import Phase):**
  - **Custom Renderer:** A dedicated renderer class for `mistune` that maps AST nodes to RTF control words.
    - `strong` -> `{\b ...}`
    - `emphasis` -> `{\i ...}`
    - `list` -> `{\listtext ...}\par ...` (Mapped to DOORS-native list RTF).
  - **RTF Wrapping:** The renderer ensures the final output is encapsulated in a standard RTF block: `{\rtf1\ansi\deff0 {\fonttbl {\f0 Arial;}} \viewkind4\uc1 \f0 <content>}`.
  - **DXL Integration:** The generated RTF string is passed to DOORS as a raw string and assigned using the DXL `richText` function: `obj."Attribute Name" = richText rtfString`. This ensures DOORS renders the formatting correctly rather than displaying raw RTF code.
- **Smart Split Logic**: When splitting large content across Excel columns [C-3], the engine shall identify structural boundaries to maintain data integrity.
    - **Excel-Side Mitigation**: To prevent data corruption from manual offline edits, the engine shall insert a `[READ-ONLY: Large content detected. Edit via GUI]` warning note into any cell belonging to a split-column set (`_1`, `_2`, etc.).
    - For **Markdown text**, it ensures markers (e.g., `**`, `[`) are not sliced.
    - For **Links and Multi-value Enums**, it ensures splits only occur at the semicolon (`;`) separator.
  - **Force-Split Implementation**: If a single structural block (e.g., a massive Markdown element or a single link entry) exceeds 32k, the parser performs a character-level split and sets a `force_split` flag in the metadata, triggering the warning required by [C-3].
- **Hybrid Table Rendering**:
  - **Structural Authority**: The transformation engine uses object-level structural markers (`TABLE_ROW`, `TABLE_CELL`) for bidirectional synchronization to bypass Excel cell limits and maintain DOORS attribute integrity [REQ-FUN-108].
  - **Readability Preview**: During export, the engine generates a GFM Markdown representation of the full table and injects it into a designated preview attribute of the `TABLE_START` object.
  - **Import Flexibility**: Supports `NEW_TABLE` markers for single-cell GFM table creation, which the engine then decomposes into DOORS objects [REQ-FUN-108.6].
- **striprtf**: Ultra-fast RTF stripping for plain-text requirements [REQ-FUN-105].

## 4. Interface Layer
- **Typer & Questionary**: For the "CLI First" and interactive wizard experiences [REQ-INF-001, REQ-INF-002].
- **PySide6**: Enterprise-grade GUI framework. Utilizes `QThread` and `qasync` for non-blocking execution [REQ-INF-002].
- **Rich**: Advanced terminal formatting for progress bars and dry-run preview tables [REQ-SYS-307, REQ-SAF-401].

## 5. Configuration & Validation
- **Pydantic v2**: Core data validation engine for Excel rows and internal data structures [REQ-FUN-217].
  - **Dynamic Schema Validation:** The tool shall dynamically generate Pydantic models based on DOORS module metadata (attribute types, lengths, and enums) to perform schema-aware validation during the Dry-Run phase [REQ-FUN-206.1].
  - **OLE Placeholder Integrity:** Validation logic shall include regex-based detection of `[IMAGE: ID]` tags to ensure they are not "Orphaned" (present in new rows) or "Duplicated" (transferred to objects that didn't originally contain them) [REQ-FUN-217.3].
- **Pydantic-Settings**: For managing environment-specific configurations and global tool settings.
- **jsonschema**: Formal validation of user-provided configuration files [REQ-INF-004]. 
  - **Primary Format**: JSON is the primary format for schema definition and tool internal state, though YAML is supported for user configuration files.

## 6. Reliability & Quality Assurance
- **Loguru**: Structured, thread-safe logging with automatic rotation for audit trails [REQ-SYS-306].
  - **Custom Log Level (NOTICE)**: Implements a `NOTICE` level with severity `22`. This level is used for significant events that are more important than `INFO` but less critical than `SUCCESS` or `WARNING`.
- **DXL Payload Management**:
  - **Chunking Limit**: The system shall limit individual DXL execution blocks to 48KB to ensure COM stability and prevent buffer overflows in the DOORS client.
  - **Iterative Buffer Accumulation**: For payloads or individual attributes (Super-Large Objects) exceeding 48KB, the tool uses an iterative DXL `Buffer` strategy [REQ-SYS-302.2, REQ-SYS-302.3]. Python segments the data into ~32KB chunks, which are sequentially transmitted and appended to a DOORS `Buffer` via COM. Once fully reconstructed in DOORS memory, the `Buffer` is committed to the module, bypassing the COM string argument limit.
- **Atomic Object Updates**: Jinja2 templates for import operations generate DXL code that groups attribute updates per object. Each object block is wrapped in a DXL error-handling structure (using `noError()`/`lastError()`) to ensure that if one attribute fails, the entire object update is aborted in DOORS memory, maintaining object-level atomicity [REQ-FUN-211].
- **Structural Integrity Enforcement**:
  - **Tri-Tiered Failure Strategy**: Implements a three-level validation check during the Dry-Run and Import phases.
    - **Tier 1 (Skip Object)**: Minor `Level` discrepancies trigger a warning but use structural markers for placement.
    - **Tier 2 (Skip Table)**: Container/Marker mismatches abort the entire table block import to prevent structural corruption.
    - **Tier 3 (Halt Module)**: Fatal errors (illegal nesting, circularity) terminate the process immediately [REQ-FUN-108.5].
  - **Structure Wins Logic**: Prioritizes `TABLE_ROW`/`TABLE_CELL` markers over the `Level` column to accommodate manual Excel re-ordering.
- **pytest & pytest-asyncio**: Core testing framework.
- **pytest-mock**: For mocking complex COM objects to achieve high unit test coverage [T-1.1].
- **Ruff & Mypy**: Static analysis tools for code quality and type safety.

## 7. Distribution & Deployment
- **PyInstaller**: Bundles the application into a standalone `.exe`. Uses custom `.spec` files to include DXL templates and assets.
- **Nuitka**: Optional compilation to C++ for performance optimization of the RTF parsing engine and basic IP protection.
