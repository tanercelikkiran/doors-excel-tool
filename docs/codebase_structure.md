# Codebase Structure: DOORS-Excel Bidirectional Tool

This document outlines the architectural organization of the DOORS-Excel Bidirectional Conversion Tool. The project follows a **Layered Architecture** to ensure separation of concerns, maintainability, and testability.

## 1. Directory Overview

```text
doors-excel-tool/
├── .github/                # CI/CD workflows and GitHub actions
├── assets/                 # Icons, images, and branding assets for the GUI
├── docs/                   # Project documentation
│   ├── requirements.md     # Functional and non-functional requirements
│   ├── technologies.md     # Technical stack and architectural principles
│   ├── ui_specification.md # UI/UX design and interaction flows
│   └── codebase_structure.md # (This document)
├── src/                    # Main source code
│   ├── doors_excel/        # Primary package
│   │   ├── api/            # Internal APIs for core logic access
│   │   ├── cli/            # CLI implementation (Typer, Questionary, Rich)
│   │   ├── gui/            # GUI implementation (PySide6, qasync)
│   │   ├── core/           # Domain logic (The "Brain" of the tool)
│   │   │   ├── diff/       # SQL-based diffing engine (SQLite)
│   │   │   ├── transformation/ # RTF/Markdown/Table transformation logic
│   │   │   └── validation/ # Pydantic models and schema validation
│   │   ├── infrastructure/ # External system integrations
│   │   │   ├── doors/      # COM/OLE bridge and DXL execution
│   │   │   ├── excel/      # OpenXML (openpyxl) and Pandas I/O
│   │   │   └── database/   # SQLite schema and persistence layer
│   │   ├── common/         # Utilities, logging, constants, and shared types
│   │   ├── resources/      # DXL templates (Jinja2), JSON schemas, and assets
│   │   └── __main__.py     # Application entry point
├── tests/                  # Test suite
│   ├── unit/               # Unit tests for isolated logic
│   ├── integration/        # Integration tests (requires DOORS/Excel)
│   └── conftest.py         # Pytest configuration and fixtures
├── .gitignore              # Git ignore rules
├── pyproject.toml          # Poetry dependency management and project metadata
├── README.md               # Project landing page and setup instructions
└── main.py                 # Convenience entry point
```

## 2. Layered Architecture Details

### 2.1 Presentation Layer (`src/doors_excel/cli/`, `src/doors_excel/gui/`)
*   **Responsibility:** Handles user interaction and provides feedback.
*   **CLI:** Uses `Typer` for commands, `Questionary` for interactive wizards, and `Rich` for terminal formatting.
*   **GUI:** Uses `PySide6` (Qt) with `qasync` to manage asynchronous operations and non-blocking COM calls.
*   **Constraint:** Must not contain business logic; it should delegate to the `core` or `api` layers.

### 2.2 API Layer (`src/doors_excel/api/`)
*   **Responsibility:** Provides a unified interface for both CLI and GUI to access the tool's core functionality.
*   **Functionality:** Orchestrates the high-level workflows (Export, Import, Validate, Rollback).

### 2.3 Core (Domain) Layer (`src/doors_excel/core/`)
*   **Responsibility:** Contains the business logic and transformation rules.
*   **`transformation/`**: Handles the complex conversion between DOORS RTF and GFM Markdown, OLE detection, and Table structural mapping.
*   **`diff/`**: Implements the 3-way merge and change detection logic using SQLite for performance and scalability (50k objects).
*   **`validation/`**: Performs data-type and structural validation of Excel data against DOORS schemas using Pydantic.

### 2.4 Infrastructure Layer (`src/doors_excel/infrastructure/`)
*   **Responsibility:** Bridges the application to external systems and data stores.
*   **`doors/`**: Manages the `pywin32` COM bridge, handles DXL execution using Jinja2 templates, and implements connection keep-alive/retry logic.
*   **`excel/`**: Provides high-fidelity I/O using `openpyxl` (including metadata management and sheet protection) and lightweight reading via `pandas`.
*   **`database/`**: Manages the SQLite lifecycle, schema migrations, and high-speed data staging for diffing.

### 2.5 Common & Resources (`src/doors_excel/common/`, `src/doors_excel/resources/`)
*   **`common/`**: Shared utilities (logging via Loguru, string manipulation, date formatting), global constants, and base exceptions.
*   **`resources/`**: Static assets, including Jinja2 DXL templates and JSON schemas for configuration validation.

## 3. Data Flow & Communication

1.  **Export:**
    - `GUI/CLI` -> `API` -> `Infrastructure (DOORS)` -> `Infrastructure (Database)` -> `Core (Transformation)` -> `Infrastructure (Excel)`.
    - Data is fetched from DOORS via DXL, staged in SQLite, converted to GFM/Excel format, and saved to a `.xlsx`/`.xlsm` file.

2.  **Import:**
    - `GUI/CLI` -> `API` -> `Infrastructure (Excel)` -> `Infrastructure (Database)` -> `Core (Validation)` -> `Core (Diffing)` -> `UI Preview`.
    - `UI Preview (User Confirmation)` -> `Infrastructure (Database)` -> `Core (Transformation)` -> `Infrastructure (DOORS)`.
    - Data is read from Excel, validated, compared to DOORS state in SQLite, presented to the user, and finally committed to DOORS via atomic DXL blocks.

## 4. Key Design Patterns
*   **Strategy Pattern:** Used for different conflict resolution policies (Excel Wins, DOORS Wins, Content-Based).
*   **Template Method:** For the general export/import workflow sequences.
*   **Observer/Signal Pattern:** Using Qt Signals and `qasync` to report progress from background infrastructure tasks to the UI.
*   **Singleton/Registry:** For managing the DOORS COM connection and the SQLite database handle.

## 5. Security & Safety Mechanisms
*   **DXL Sanitization:** Strict templating in `infrastructure/doors/` to prevent injection.
*   **Atomic Updates:** Grouping DXL operations in `core/` to ensure object-level atomicity.
*   **Metadata Integrity:** Checksum verification in `infrastructure/excel/` to prevent tampering with read-only data.
*   **Rollback Snapshots:** Persistent state in `infrastructure/database/` allowing for recovery from failed sessions.
