# Project Requirements: IBM DOORS - Excel Bidirectional Conversion Tool

## 1. Introduction
The goal of this project is to develop a tool that facilitates seamless bidirectional data exchange between IBM DOORS and Microsoft Excel. The tool utilizes DXL (DOORS eXtension Language) snippets via COM/OLE to execute queries and manage data transfer.

## 2. Interface Requirements
- **[REQ-INF-001] CLI First:** The tool shall provide a comprehensive Command Line Interface (CLI) for automation and batch processing. (Verification: Demo)
- **[REQ-INF-002] Interactive Mode:** The tool shall provide an interactive mode (or optional GUI) for guided mapping and module selection. (Verification: Demo)
- **[REQ-INF-003] Configuration-Driven:** All operations shall be executable using a configuration file (JSON/YAML) to ensure repeatability. (Verification: Test)
- **[REQ-INF-004] Schema Validation:** The tool shall validate the configuration file against a predefined schema (e.g., JSON Schema) before execution. (Verification: Test)

## 3. Functional Requirements

### 3.1. DOORS to Excel Export (E-X)
- **[REQ-FUN-101] Scope Definition:** Extract data from a specified DOORS module using its full path or unique URL (e.g., `doors://...`). 
  - **URL Support:** The tool shall parse DOORS URLs to identify the server, port, and module handle. (Verification: Test)
- **[REQ-FUN-102] Baseline Support:** Users must be able to specify a Baseline (Major.Minor) or the "Current" version for export. (Verification: Test)
- **[REQ-FUN-103] Attribute Selection:** Users must be able to select a subset of DOORS attributes for export. (Verification: Test)
- **[REQ-FUN-104] Hierarchy Representation:** 
  - The tool shall include a "Level" column indicating the object's depth.
  - The tool shall include a "Parent Absolute Number" column to maintain structural integrity for re-import. (Verification: Test)
- [REQ-FUN-105] **Rich Text & Formatting Preservation:** 
  - The tool shall always use GitHub Flavored Markdown (GFM) as an intermediate format to preserve DOORS formatting (bold, italic, lists, etc.) during export to Excel and vice-versa.
  - **Transformation Logic:** The tool will map RTF control words (e.g., \b, \i) to GFM equivalents (e.g., **, *). For complex structures like nested lists, it will prioritize text integrity.
  - **Policy: Best-Effort Preservation:** If a specific formatting element cannot be converted to/from GFM, the tool shall fallback to Plain Text (within the GFM string) for that specific element/object and continue the process without interruption.
  - **[REQ-FUN-105.2] Fallback Logging:** Every occurrence of a formatting fallback (RTF to Plain Text) shall be logged as a "Warning" referencing the Absolute Number and, if identifiable, the unsupported RTF element/structure. (Verification: Test)
- **[REQ-FUN-105.4] Unmodified RTF Restoration (No-Change Bypass):** To prevent the loss of RTF features that cannot be represented in Markdown (e.g., colors, highlights, specific font sizes), the tool shall:
  - **Export:** Store the original DOORS RTF and a SHA-256 hash of the generated Markdown in the local SQLite cache [REQ-FUN-116].
  - **Import:** If the current Excel cell content's hash matches the stored Markdown hash, the tool shall restore the original RTF from the cache instead of re-converting from Markdown.
  - **Graceful Fallback:** If the cache is unavailable or the hashes do not match, the tool shall use the standard Markdown-to-RTF renderer [REQ-FUN-105.3]. (Verification: Test)
- **[REQ-FUN-105.5] Rich Format Loss Confirmation:** If a user modifies an Excel cell that originally contained DOORS-specific rich formatting (e.g., colors, specific fonts, nested tables) as identified by the RTF parser [REQ-FUN-105.1], the tool shall:
  - **Detection:** Identify that the original RTF contained "Rich" elements that cannot be reconstructed from Markdown.
  - **Risk Flagging:** Flag this change as "Potential Data Loss (Formatting)" during the Dry-Run phase [REQ-SAF-401].
  - **Interactive/GUI:** Require the user to explicitly acknowledge the loss of rich formatting for each affected attribute via a "Format Loss Review Gate".
  - **Headless CLI:** Require the user to provide the `--accept-format-loss` flag. If not provided, the tool shall skip the update for that specific attribute to preserve the original DOORS content. (Verification: Test)
- [REQ-FUN-105.1] **RTF Parsing:** The tool shall use a robust RTF parser (rtfparse) to identify formatting boundaries before Markdown conversion. (Verification: Test)
- [REQ-FUN-105.3] **Markdown to RTF Conversion:** For import operations, the tool shall convert GFM text from Excel back into native DOORS RTF. 
  - **Renderer Logic:** The tool shall use a custom renderer (via mistune AST) to map GFM elements (bold, italic, lists) to their RTF control word equivalents (e.g., `**text**` -> `{\b text}`).
  - **Structure:** The resulting RTF must be wrapped in a valid DOORS-compatible RTF header (e.g., `{\rtf1\ansi...}`) to ensure the DOORS `richText` function correctly interprets the formatting. (Verification: Test)
- **[REQ-FUN-106] OLE Detection:** Flag objects containing OLE items (images, embedded files) in a dedicated "Has OLE" column. (Verification: Test)
- **[REQ-FUN-107] Link Export:**
  - Export "In-links" and "Out-links" as quote-aware semicolon-separated lists. 
  - **Read-Only In-links:** "In-links" are exported for informational purposes only. The tool shall treat "In-link" columns as read-only during import, as modifying them requires write access to external source modules [Constraint: DOORS Lock Management].
  - **[REQ-FUN-107.1] Link Metadata Format:** Each link entry shall follow the format: `[TargetID] (Type: "LinkTypeName", Mod: "LinkModuleName")`.
    - **Robust Parsing:** The tool shall always wrap `LinkTypeName` and `LinkModuleName` in double quotes. To handle semicolons or quotes within these names, the tool shall use CSV-style escaping: any double quotes within these names must be escaped by doubling them (e.g., `""`).
    - **Separator Policy:** Semicolons (`;`) shall be used to separate multiple link entries within a single Excel cell. The parser must use a quote-aware splitting logic to ignore semicolons located inside the quoted `LinkTypeName` or `LinkModuleName`. (Verification: Test)
  - **[REQ-FUN-107.2] Cross-Module Links:** The tool shall support links to/from objects in different modules within the same database by using the full module path. (Verification: Test)
  - **[REQ-FUN-107.3] Link Parsing Regex:** To ensure bidirectional consistency, link entries shall be parsed using the following formal regex: `^(?:(?P<action>DEL):)?\s*(?:\[(?P<id>[^\]]+)\]\s*\(Type:\s*"(?P<type>(?:[^"]|"")*?)",\s*Mod:\s*"(?P<mod>(?:[^"]|"")*?)"\)|(?P<target>doors://\S+|\d+))$`. This regex supports deletions, full metadata links, and simple targets (Absolute Numbers or URLs). (Verification: Test)
- [REQ-FUN-108] **Table Handling:** 
  - DOORS Tables (Table, Row, and Cell objects) must be exported while maintaining their logical sequence.
  - **[REQ-FUN-108.1] Structural Markers:** The tool shall use a "Object Type" column to identify table structures.
    - **Standardized Defaults:** The following default values shall be used: 
      - `TABLE_START`: Used for synchronizing existing tables. Requires a valid Absolute Number.
      - `TABLE_ROW`, `TABLE_CELL`, `TABLE_END`: Standard structural markers.
      - `NEW_TABLE`: Used to generate an entirely new structural table from scratch.
      - `OBJECT`: Standard DOORS object.
    - **Configurability:** These markers shall be configurable via the project configuration file.
    - **Metadata Persistence:** To ensure cross-user compatibility, the active marker mapping shall be embedded into the Excel Workbook's Custom Properties during export. (Verification: Test)
  - **[REQ-FUN-108.2] Structural Validation:** The tool shall strictly verify the sequence of markers (e.g., every `TABLE_ROW` must be within a `TABLE_START`/`TABLE_END` block) before import. If markers are malformed or missing due to manual Excel edits, the tool must abort the import of that specific table and log a critical error to prevent structure corruption. (Verification: Test)
  - **[REQ-FUN-108.5] Hierarchy Reconciliation & Failure Strategy:** 
    - **Policy: Structure Wins:** If an object is marked with a table structural marker (`TABLE_ROW`, `TABLE_CELL`), these markers shall take precedence over the `Level` column for object placement.
    - **Tri-Tiered Failure Strategy:**
      - **Tier 1: Skip Object (Warning):** If the `Level` column contradicts the table structure, the tool uses markers to place the object and logs a warning.
      - **Tier 2: Skip Table (Critical Error):** If the `Parent Absolute Number` contradicts the table's container or if structural markers (`TABLE_START`/`TABLE_END`) are malformed, the tool shall abort the import of that specific table block.
      - **Tier 3: Halt Module (Fatal Error):** If illegal nesting or circular table dependencies are detected, the tool shall halt the entire import process to prevent database corruption. (Verification: Test)
  - **[REQ-FUN-108.6] Hybrid Table Strategy:**
    - **Export Preview:** For enhanced readability in Excel, the `TABLE_START` object shall include a read-only GFM Markdown "Preview" of the entire table.
    - **Import Authority:** While `NEW_TABLE` markers support single-cell GFM input for new tables, structural markers (`TABLE_ROW`, `TABLE_CELL`) remain the authoritative source for updating existing DOORS tables to ensure attribute-level integrity. (Verification: Analysis)
  - **[REQ-FUN-108.7] Excel Structural Protection:** To prevent users from accidentally corrupting the DOORS table hierarchy in Excel (e.g., deleting a `TABLE_END` marker or re-ordering rows), the tool shall implement "Structural Protection":
    - **Cell Locking:** During export, all cells containing structural markers (`TABLE_START`, `TABLE_ROW`, `TABLE_CELL`, `TABLE_END`), Absolute Numbers, and hierarchy metadata (`Level`, `Parent Absolute Number`) shall be set to "Locked".
    - **Attribute Permissibility:** Cells containing editable DOORS attributes (e.g., `Object Text`, `Status`) for these structural objects shall remain "Unlocked".
    - **Sheet Protection:** The tool shall apply Excel "Sheet Protection" to the exported worksheets. This protection shall allow users to select locked/unlocked cells but prevent deleting rows, inserting rows, or modifying locked cells.
    - **Configurability:** Users shall be able to enable/disable this protection during export. An optional password for sheet protection may be provided via configuration. (Verification: Test)
  - **[REQ-FUN-108.4] Table Cell Fallback:** Because DOORS table cells can contain complex OLE objects which cannot be perfectly mapped to Excel cells, the tool shall fallback to plain text for unsupported elements within tables, heavily leveraging the warnings defined in [REQ-FUN-105.2]. (Verification: Test)
  - **[REQ-FUN-108.3] Table Attributes:** Specific table-level attributes (e.g., width, border) are ignored during export/import unless explicitly mapped in the "Table Attribute Mapping" configuration. These mappings shall also be persisted in the Excel metadata. (Verification: Analysis)
- **[REQ-FUN-109] Metadata Export:** Include "Last Modified On", "Last Modified By", and "Source Baseline" as read-only reference columns. (Verification: Test)
- **[REQ-FUN-110] View-Based Export:** 
  - Users shall be able to select a specific DOORS View for the export process.
  - The tool shall automatically identify and export the attributes displayed in the selected view. (Verification: Test)
- **[REQ-FUN-111] Filter & Sort Respect:** The tool shall honor the filtering and sorting logic defined in the selected DOORS View. (Verification: Test)
- **[REQ-FUN-113] Bulk Export:** Support exporting multiple modules from the same project into a single Excel workbook (one worksheet per module).
  - **[REQ-FUN-113.1] Sheet Naming & Uniqueness:** 
    - Worksheets shall be named using the convention: `Sanitize(ModuleName)[:22] + "_" + CRC32(FullModulePath)`. 
    - **Sanitization Logic:**
      - The `Sanitize` function shall first trim leading and trailing whitespace from the `ModuleName`.
      - It shall then replace any of the forbidden Excel characters (`\`, `/`, `?`, `*`, `[`, `]`, `:`) with a single underscore (`_`).
    - The `CRC32` hash shall be represented as an **8-character hexadecimal string** (zero-padded).
    - This ensures uniqueness for modules with identical names located in different DOORS folders while leaving a safety buffer under the 31-character Excel limit (22 + 1 + 8 = 31). (Verification: Test)
  - **[REQ-FUN-113.2] Module Identification:** The tool shall use **Sheet-Scoped Hidden Defined Names** (e.g., `_DOORS_Module_Path`) to store the full DOORS module path/URL within each worksheet. This ensures that metadata persists even if the sheet is moved between workbooks or renamed. (Verification: Test)- [REQ-FUN-114] **Image Placeholders:** Use `[IMAGE: ID]` placeholders within the Markdown text to indicate image locations. The `ID` shall be a sequential integer representing the image's order within that specific object (e.g., `[IMAGE: 1]`). (Verification: Test)
- [REQ-FUN-115] **Multi-Value Enum Handling:** Multi-value Enumeration attributes (where DOORS allows selecting multiple options) shall be exported/imported using CSV-style (RFC 4180) semicolon-separated strings in Excel. If an enumeration value contains a semicolon (`;`) or a double quote (`"`), the value must be enclosed in double quotes, and any internal double quotes must be doubled (e.g., `Option A; "Option; with; semicolon"; "Option with ""quotes"""`). (Verification: Test)
- [REQ-FUN-117] **Metadata Integrity (Export):** To prevent unauthorized modification of read-only reference data, the tool shall calculate a cryptographic hash (SHA-256) of all protected metadata fields (e.g., `Source Baseline`, `_DOORS_Module_Path`, and Absolute Numbers) during export. This checksum shall be stored as a hidden Workbook Property or a Sheet-Scoped Hidden Defined Name within the Excel file. (Verification: Test)

### 3.2. Excel to DOORS Import (I-M)
- **[REQ-FUN-201] Primary Key:** Use DOORS "Absolute Number" as the unique identifier. (Verification: Test)
- **[REQ-FUN-202] Target Validation:** The tool **must** verify that the target module is the "Current" version and is opened in "Edit" mode. (Verification: Test)
- **[REQ-FUN-203] Object Creation & Placement:**
  - Rows without an Absolute Number are treated as "New".
  - **[REQ-FUN-203.1] Placement Columns:** "New" objects require a Parent ID and Placement (After/As Child) to be specified. Default column headers are `_Parent_ID` and `_Placement`, but these shall be configurable.
  - **[REQ-FUN-203.2] Default Placement:** If no placement is specified, new objects are appended to the end of the module. (Verification: Test)
- **[REQ-FUN-204] Hierarchy Updates:** If an existing object's Parent ID changes in Excel, the tool shall attempt to move the object in DOORS.
- **[REQ-FUN-205] Move Optimization:** The tool shall optimize object movements to minimize DXL execution time (e.g., re-ordering siblings locally before performing deep moves). (Verification: Analysis)
- **[REQ-FUN-206] Type-Safe Attribute Mapping:**
  - Validate values against DOORS Enumeration types before import.
  - **[REQ-FUN-206.1] DOORS Length Validation:** 
    - Attributes of type "String" shall be limited to 1024 characters.
    - Attributes of type "Text" (Rich Text) are subject to the Smart Split logic [C-3] but are otherwise unconstrained by length in DOORS.
    - Exceeding these limits during validation shall be flagged as a "Blocking Error". (Verification: Test)
  - Prevent writing to Read-Only or System attributes.
  - Validate Date formats against DOORS locale settings. (Verification: Test)
- [REQ-FUN-207] **Conflict Resolution:**
  - **Conflict Definition:** A conflict is detected when both the DOORS object and its corresponding Excel row have been modified since the "Source Baseline" recorded in the Excel metadata.
  - **Policy: Excel Overwrites (Default):** Blind synchronization. Excel values take precedence regardless of DOORS state.
  - **Policy: DOORS Overwrites (Skip):** If a conflict is detected, the Excel change is ignored and the DOORS state is preserved.
  - **Policy: Content-Based (3-Way Merge):** The tool performs an attribute-level 3-way merge using the "Source Baseline" as the common ancestor. 
    - If changes are disjoint (different attributes modified), both are kept. 
    - **Conflict Resolution Gate:** If the same attribute is modified in both DOORS and Excel, the tool shall flag the change as a "Conflict" requiring manual resolution.
      - **Interactive/GUI:** The user must explicitly choose between DOORS value, Excel value, or a manual merge via the Conflict Resolution Gate.
      - **Headless CLI:** The user must provide a conflict resolution strategy (e.g., `--resolve-conflicts=excel` or `--resolve-conflicts=doors`). If no strategy is provided, the tool shall skip the conflicting attribute and log a warning. (Verification: Test)
- **[REQ-FUN-208] Baseline Mismatch Warning:** Warn if the "Source Baseline" in Excel differs from the Current module's last baseline. (Verification: Test)
- **[REQ-FUN-209] Deletion/Deactivation:** 
  - **Option: Ignore (Default):** DOORS objects missing from Excel are left unchanged.
  - **Option: Soft-Delete:** Mark missing objects by setting a designated attribute (configurable, default: `Status`) to `Deleted`.
  - **Option: Purge:** Physically delete objects from DOORS.
  - **[REQ-FUN-209.1] Purge Safeguard:** Purge operations require an explicit "--force" flag in CLI and a secondary confirmation in interactive mode. (Verification: Test)
  - **[REQ-FUN-209.2] Cascading Delete Warning:** The tool shall detect and warn users about "Indirect Deletions". In DOORS, deleting a "Parent" object automatically deletes all its "Children". If a user marks a parent for deletion (Purge) in Excel but does not explicitly mark the children, the Dry-Run phase must identify these children and include them in the deletion count/list with an "Indirect" or "Cascading" status to prevent accidental data loss. (Verification: Test)
- **[REQ-FUN-210] OLE Protection:** 
  - If a DOORS attribute contains OLE and the Excel cell text (after stripping Markdown tags) matches the DOORS plain-text representation, the tool **must not** perform a write operation.
  - **[REQ-FUN-210.1] OLE Overwrite Confirmation:** If an Excel modification targets a DOORS attribute containing OLE, the tool shall flag the change as potential data loss. 
    - **Interactive/GUI:** User must explicitly confirm overwrites in the OLE Review Gate.
    - **Headless CLI:** The user must provide `--accept-ole-overwrites` to proceed. If neither `--accept-ole-overwrites` nor `--reject-ole-overwrites` is provided, the tool shall default to **rejecting** the update for that specific attribute to prevent accidental loss. (Verification: Test)
  - **[REQ-FUN-210.3] OLE Fallback (Rejection):** If a user rejects an OLE overwrite, the tool shall **discard the change for that specific attribute**. The original DOORS content (including text and OLE) shall be preserved. Updates to other non-conflicting attributes for the same object shall proceed normally.
  - **[REQ-FUN-210.2] No Bidirectional OLE:** Importing new OLE objects or images from Excel to DOORS is explicitly out of scope. (Verification: Test)- [REQ-FUN-211] Atomic & Clean Updates:
  - **Object-Level Atomicity:** The tool shall group all attribute updates for a single object into a single DXL execution block. If any attribute update within that block fails (e.g., due to a DOORS trigger or unexpected type error), the tool shall ensure that no changes are applied to that specific object, effectively treating the object update as an atomic operation.
  - Only update attributes that have actually changed (case-sensitive).
  - Trim leading/trailing whitespace unless disabled.
  - Group attribute updates per object to minimize history entries. (Verification: Test)
- [REQ-FUN-212] Table Integrity Management:
  - Allow updates to text/attributes of existing "Cell" objects.
  - Support adding/deleting "Row" objects if Excel structure is consistent.
  - Support creating entirely new tables using "NEW_TABLE" markers.
  - **[REQ-FUN-212.1] Structural Validation:** Verify row/cell counts and structural markers before execution. (Verification: Test)
- **[REQ-FUN-213] Link Management:**
  - **[REQ-FUN-213.1] Out-link Management:** Create new "Out-links" or delete existing ones by entering/modifying targets in a designated link column. 
  - **Restriction:** Creation of "In-links" (incoming from other modules) is not supported, as it would require managing write locks on external modules.
  - **[REQ-FUN-213.2] Link Deletion:** Use "DEL:" prefix in the link column to remove specific "Out-links". The tool shall use the regex defined in [REQ-FUN-107.3] to identify the action and the target. (Verification: Test)
- **[REQ-FUN-214] Circular Link Detection:** The tool shall detect and prevent the creation of circular link dependencies using graph analysis. 
  - **Lightweight Extraction:** To support large modules (up to 50k objects), the tool shall perform a dedicated, batched DXL extraction of link edges (Source ID -> Target ID) separate from full attribute data.
  - **Dynamic Analysis:** This check must be performed during the Dry-Run phase, incorporating both existing DOORS links and proposed changes from Excel. (Verification: Test)
- **[REQ-FUN-215] Bulk Import:** Process all worksheets in an Excel file. 
  - **[REQ-FUN-215.1] Identification Hierarchy:** The tool shall resolve worksheet-to-module mapping using the following priority:
    1. **Worksheet Metadata:** Embedded DOORS URL/Path in Workbook/Worksheet properties.
    2. **Workbook Mapping:** Explicit mappings defined in the project configuration file.
    3. **CRC32 Match:** Sheet names matching the `Sanitize(ModuleName)[:22] + "_" + CRC32(FullModulePath)` convention [REQ-FUN-113.1].
    4. **Literal Name:** Case-insensitive match of the sheet name to a DOORS module in the target folder.
  - Worksheets that cannot be matched shall be ignored with a log entry. (Verification: Test)
- **[REQ-FUN-216] Character Escaping:** All user-provided strings passed to DXL must be properly escaped (e.g., handling backslashes, quotes, and newlines) to prevent DXL script errors. (Verification: Test)
- **[REQ-FUN-217] Pre-Import Validation (Static):** Before any DOORS interaction, the tool shall perform a full structural and data-type validation of the Excel file.
  - **Checklist:** Missing mandatory columns, invalid Enumeration values, illegal characters for DOORS, and schema compliance.
  - **[REQ-FUN-217.1] Attribute Schema Verification:** The tool shall fetch the target module's attribute definitions (Types and Limits) from DOORS during the initialization phase of validation to ensure type-safe checks.
  - **[REQ-FUN-217.2] Validation Error Persistence:** To support modules with 50,000+ objects [REQ-PER-503], all validation errors shall be persisted in the local SQLite database. This enables UI virtualization of the error list and prevents memory exhaustion when dealing with high error density. (Verification: Analysis)
  - **[REQ-FUN-217.3] OLE Placeholder Validation:** The tool shall detect "Orphaned" or "Duplicated" OLE placeholders (e.g., `[IMAGE: ID]`) in Excel. Since importing new OLE objects is out of scope [REQ-FUN-210.2], any placeholder found in a "New" row (no Absolute Number) or a row where the original DOORS object did not contain that specific OLE index shall be flagged as a validation error. This prevents users from accidentally creating literal text objects like "[IMAGE: 1]" in DOORS. (Verification: Test)
  - **Outcome:** Reports all "Blocking" errors that must be fixed in Excel before proceeding. (Verification: Test)
- **[REQ-FUN-218] Post-Import Verification:** After import, the tool shall optionally verify that the changes were correctly applied in DOORS by performing a quick re-read of the modified objects. (Verification: Test)
- **[REQ-FUN-219] Link Target Resolution:** 
  - To support imports, the tool shall resolve link targets using a multi-stage approach:
    - **Local Resolve:** Simple Absolute Numbers are resolved within the current module.
    - **Global Resolve:** Full metadata format or DOORS URLs are used for cross-module links.
  - **Auto-Open:** The tool shall automatically open target modules in "Read" mode (if not already open) to resolve IDs for Out-link creation. (Verification: Test)

### 3.3. System & Connectivity (S-C)
- **[REQ-SYS-301] DOORS Connection:**
  - Automatically detect a running DOORS instance.
  - Support specifying a target DOORS database/port if multiple instances are present. (Verification: Demo)
- **[REQ-SYS-302] DXL Query Mechanism:**
  - Use parametric DXL templates for logic execution.
  - Use `Buffer` objects for performance with large strings.
  - **[REQ-SYS-302.1] DXL Script Chunking:** Split large data payloads into multiple DXL executions (max 48KB per chunk) to avoid COM script size limits and buffer overflows. (Verification: Inspection)
- **[REQ-SYS-303] DXL Memory Management:** The tool shall explicitly release DXL objects (e.g., `delete(buffer)`, `close(file)`) to prevent memory leaks in the DOORS client process. (Verification: Inspection)
- **[REQ-SYS-304] Batch Processing:** Process large modules (>1000 objects) in configurable batches to prevent COM timeouts and memory leaks. (Verification: Test)
- **[REQ-SYS-305] Version Compatibility:** The tool shall verify the DOORS client version and abort if it falls outside the supported range (e.g., < 9.6). (Verification: Test)
- **[REQ-SYS-306] Structured Logging:** The tool shall implement thread-safe, structured logging with automatic rotation for audit trails and debugging. 
- **[REQ-SYS-306.2] Notice Level:** A custom "Notice" log level (Severity: 22) shall be implemented between INFO and SUCCESS to highlight significant events that require user awareness but do not constitute warnings. (Verification: Inspection)
- **[REQ-SYS-306.1] Audit Trail Export:** The tool shall generate a machine-readable JSON change summary for every successful import session. (Verification: Test)
- **[REQ-SYS-307] Signaling & Progress Tracking:** 
  - The tool shall implement a non-blocking signaling mechanism to provide real-time updates from the DXL engine to the UI/CLI.
  - **Multi-Level Progress:** Support tracking of Global task progress, Batch progress, and internal DXL Chunk progress.
  - **Thread Isolation:** Long-running COM/DXL operations must be isolated in background threads to prevent UI freezing. (Verification: Demo)
- **[REQ-SYS-308] Session Keep-Alive:** To prevent DOORS session timeouts during long-running batch operations [REQ-PER-503], the tool shall implement a background keep-alive mechanism. This mechanism shall periodically send a minimal "ping" DXL command (e.g., `print ""`) to the DOORS COM interface at a configurable interval (default: 60 seconds) whenever a long operation is active but not actively communicating with the COM bridge. (Verification: Test)
- **[REQ-FUN-116] SQLite Cache Layer:** To handle up to 50,000 objects [REQ-PER-503] without blocking the UI, the tool shall perform diff calculations in a background worker and store results in a local SQLite database for efficient pagination and sorting. (Verification: Analysis)
- **[REQ-SYS-302.2] Large Payload Accumulation:** Payloads exceeding 48KB shall be transmitted using an iterative DXL `Buffer` accumulation strategy. The payload shall be split into ~32KB chunks in Python and reconstructed within DOORS memory to prevent COM buffer overflows. (Verification: Test)
- **[REQ-SYS-302.3] Super-Large Object Handling:** For individual objects where a single attribute (e.g., Object Text) exceeds 48KB, the tool shall apply the iterative accumulation strategy [REQ-SYS-302.2] per attribute to ensure successful export and import of massive data points. (Verification: Test)
- **[REQ-SAF-405.1] Session Integrity Validation:** The `.session.json` file shall store the SHA-256 hash of the source Excel file and the target DOORS module version. Resumption shall be blocked if a mismatch is detected, unless an explicit `--force-resume` flag is used. (Verification: Test)
- **[REQ-INF-001.1] Non-Interactive Dry-Run:** In CLI mode, the mandatory Dry-Run [REQ-SAF-401] shall be satisfied by logging a formatted diff table to stdout and generating a machine-readable JSON report. The process shall require a `--yes` flag for automatic execution in CI/CD. (Verification: Demo)

### 3.4. Safety and Reliability (S-R)
- **[REQ-SAF-401] Dry-Run / Preview (Dynamic):** After successful Validation, the tool shall compare Excel data with the current DOORS state to generate a detailed impact report.
  - **Checklist:** Identify "New", "Updated", "Moved", and "Deleted" objects. Check for module locks, baseline mismatches, and circular links [REQ-FUN-214].
  - **Outcome:** A visual summary and object-level diff that requires explicit user confirmation before execution.
  - **[REQ-SAF-401.1] Pagination:** For large modules, the preview shall support pagination to maintain performance and readability. (Verification: Demo)
- **[REQ-SAF-402] Error Feedback:** Optionally create a `_DOORS_Validation_Feedback` column in the Excel file for line-by-line feedback.
  - **Pollution Prevention:** Upon starting a new validation or import run, the tool shall automatically ignore and clear any existing data in the `_DOORS_Validation_Feedback` column to prevent data pollution from previous sessions. (Verification: Test)
- **[REQ-SAF-403] Module Management:**
  - Verify module is open in "Edit" mode before import.
  - **[REQ-SAF-403.1] Lock Failure Handling:** If the tool cannot acquire an "Edit" lock (e.g., module opened by another user), it shall report the user holding the lock and terminate gracefully. (Verification: Test)
- **[REQ-SAF-404] Permission Enforcement:** Strictly inherit DOORS access rights; block unauthorized updates. (Verification: Test)
- [REQ-SAF-405] **Error Logging & Restartability:** If a critical error occurs (e.g., COM disconnection), the tool shall save its current state (last processed object ID, pending changes, configuration) to a temporary JSON state file (`.session.json`). Upon restart, the tool shall detect this file and allow the user to resume or restart the process.
  - **CLI Behavior:** In non-interactive CLI mode, the tool must abort execution if a `.session.json` is detected unless explicitly invoked with `--resume` or `--discard-session` flags. (Verification: Test)
- [REQ-SAF-406] **Rollback Backup (Snapshot):** During the Dry-Run phase [REQ-SAF-401], the tool shall store the current "Original" values of all DOORS objects identified for modification in the local SQLite cache [REQ-FUN-116].
- [REQ-SAF-406.1] **Manual Rollback:** In the event of a partial failure or user-initiated cancellation, the tool shall provide a 'Generate Rollback Excel' function. This function uses the SQLite snapshot to create an Excel file that is fully compatible with the standard import workflow, allowing the user to restore affected objects to their pre-session state.
  - **Purge Constraint:** The Rollback Excel cannot recover objects that have undergone a Purge (physical deletion) operation; it will recreate them as new objects with new Absolute Numbers in DOORS. (Verification: Demo)

## 4. Non-Functional Requirements

### 4.1. Performance
- **[REQ-PER-501] Export Speed:** The tool shall export at least 100 objects per second for standard text attributes. (Note: Markup conversion is mandatory to preserve formatting structure).
- **[REQ-PER-502] Import Speed:** The tool shall update at least 20 objects per second in DOORS.
- **[REQ-PER-503] Large Module Support:** The tool shall handle modules with up to 50,000 objects. Pagination must be used for UI-heavy operations like Dry-Run previews to maintain responsiveness.

### 4.2. Reliability & Robustness
- **[REQ-REL-601] Partial Success:** If an error occurs during an object update, the tool shall log the error and continue with the next object, unless it is a fatal connection failure.
- **[REQ-REL-602] Session Recovery:** If the connection to DOORS is lost, the tool shall attempt to reconnect up to 3 times before terminating.

### 4.3. Security
- **[REQ-SEC-701] No Credential Storage:** The tool shall not store DOORS passwords. It relies on the existing authenticated DOORS session.
- **[REQ-SEC-702] DXL Sanitization:** All DXL snippets must be generated using templates that prevent DXL injection attacks.

## 5. Technical Constraints
- **C-1:** IBM DOORS client (v9.6 or 9.7) must be installed and authenticated.
- **C-2:** Excel formats: `.xlsx` or `.xlsm` (OpenXML) only.
- [C-3] **Character Limit Handling & Data Integrity:** 
  - Any cell content exceeding 32,767 characters (Excel limit)—including "Object Text", "In-links/Out-links", and "Multi-value Enum" columns—shall be partitioned into indexed columns using a fixed suffix: `[Attribute Name]_1`, `[Attribute Name]_2`, etc. 
  - **Smart Split:** The partitioner shall ensure that structural elements are not split between columns.
    - **Text Attributes:** Markdown markers (e.g., `**`, `_`, `[`) and logical boundaries (e.g., newlines) shall be preserved.
    - **Link & Enum Columns:** The split shall only occur at the semicolon (`;`) separator—using quote-aware logic to ignore semicolons within quoted values—to ensure each entry (link metadata or enum value) remains intact within a single cell.
  - **[C-3.1] Force-Split Fallback:** If a single structural element (e.g., a massive Markdown block or a single link entry that alone exceeds 32k) exceeds 32,767 characters, a **Force-Split** shall occur at the character limit.
    - **Warning Requirement:** A warning shall be logged for each Force-Split, specifying the object ID and the affected attribute, as formatting or parsing integrity in Excel will be compromised. (Verification: Test)
  - **Excel-Side Editing Restriction:** For attributes exceeding the 32,767 character limit (split into `_1`, `_2`, etc.), the tool shall insert a warning note/text into the affected cells (e.g., `[READ-ONLY: Large content detected. Edit via GUI to prevent data corruption]`) to discourage manual offline editing, as maintaining integrity across split columns is high-risk. (Verification: Inspection)
  - During import and in the UI, these shall be concatenated and presented as a single unified field.
  - **Auto-Split on Save:** When a user modifies a unified field in the UI or an import runs, the system shall automatically trigger the Smart Split partitioner in the background to safely re-slice the data into chunks before writing back to Excel, without requiring manual user intervention. (Verification: Analysis)
  - **DXL Alignment:** The partitioning for Excel [C-3] is independent of the iterative DXL `Buffer` accumulation [REQ-SYS-302.2], which handles transport limits. All partitioned columns are re-joined into a single `Buffer` before transmission to DOORS.
  - **C-4:** Environment: Python 3.10+ with `pywin32`, `pandas`, and `openpyxl`.
- **C-5:** Baseline Immutability: Explicitly check `isBaseline(Module)` before write operations.
- **C-6:** Network: Minimal latency required for COM/OLE stability; high-latency connections should increase timeout settings.
- **C-7:** **Excel Formula Handling**: During the import phase, the tool must read Excel files using the `data_only=True` parameter (via `openpyxl`). This is mandatory to ensure that the tool captures the calculated results of formulas rather than the raw formula strings, preventing data corruption in DOORS.

## 6. Testing Requirements
- **T-1.1: Unit Testing:** High coverage (>80%) for the Excel parsing and DXL generation logic.
- **T-1.2: Integration Testing:** Automated tests using a test DOORS project to verify export/import accuracy.
- **T-1.3: Round-Trip Testing:** Ensure an export-then-import cycle of an unmodified module results in zero changes in DOORS.

## 7. Risk Analysis & Mitigations

| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| **Table Corruption** | High | REQ-FUN-212.1: Strict structural validation. |
| **Baseline Overwrite** | High | C-5 & REQ-FUN-202: Explicit status checks. |
| **DXL Memory Leak** | Medium | REQ-SYS-303: Explicit memory management. |
| **OLE/Images Loss** | High | REQ-FUN-210: OLE Protection logic. |
| **COM/DXL Timeouts** | Medium | REQ-SYS-304: Batching logic. |
| **Circular Links** | High | REQ-FUN-214: Graph-based detection during Dry-Run. |
| **DXL Injection** | High | REQ-FUN-216 & REQ-SEC-702: Sanitization. |
| **Lock Contention** | Medium | REQ-SAF-403.1: Graceful lock failure handling. |
| RTF Formatting Loss | Medium | REQ-FUN-105.4: Hash-based original RTF restoration for unmodified cells. |
| **Split Column Integrity [C-3]** | High | C-3: Smart splitting, Excel-side read-only warnings, and mandatory GUI editing for large content. |

## 8. Glossary
- **Absolute Number:** Unique immutable ID in DOORS.
- **Baseline:** Read-only snapshot of a module.
- **COM/OLE:** Communication bridge between Python and DOORS.
- **DXL:** DOORS eXtension Language.
- **Module:** A structured document in DOORS.

## 9. Assumptions
- **A-1:** User has an active DOORS session.
- **A-2:** Network to DOORS DB is stable.
- **A-3:** User has "Modify" or "Admin" access for import operations.

