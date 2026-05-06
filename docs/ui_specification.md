# UI/UX Specification: DOORS-Excel Bidirectional Tool

## 1. Introduction
This document outlines the user interface and user experience design for the DOORS-Excel Bidirectional Conversion Tool. The tool is designed to provide a seamless, safe, and efficient way for Requirements Engineers and Project Managers to exchange data between IBM DOORS and Microsoft Excel.

### 1.1 Design Goals
*   **Efficiency:** Streamline repetitive tasks with CLI automation and intuitive interactive modes.
*   **Safety First:** Prevent accidental data loss or corruption in DOORS through dry-runs, validations, and clear warnings.
*   **Transparency:** Provide detailed feedback, progress tracking, and audit logs for every operation.
*   **Flexibility:** Support both power users (CLI) and occasional users (GUI/Interactive CLI).

---

## 2. User Personas
*   **Requirements Engineer (Power User):** Focuses on bulk updates, complex mapping, and automated syncs. Prefers CLI and configuration files.
*   **Quality Manager (Occasional User):** Performs exports for reviews or simple imports. Prefers a guided GUI or interactive wizard.
*   **Admin:** Sets up project-wide configuration files and mapping schemas.

---

## 3. Command Line Interface (CLI)
Built with **Typer**, the CLI is the primary interface for automation.

### 3.1 Command Structure
```bash
doors-excel [COMMAND] [OPTIONS]
```

### 3.2 Commands
*   `export`: Extract data from DOORS to Excel.
*   `import`: Load data from Excel to DOORS.
*   `validate`: Perform a non-destructive check of a configuration file [REQ-INF-004] or an Excel file [REQ-FUN-217] against the target DOORS module schema and data types.
*   `rollback-excel`: Generate a recovery Excel file based on a previous session's SQLite snapshot to restore DOORS to its pre-import state [REQ-SAF-406.1].
*   `gui`: Launch the graphical user interface [REQ-INF-002].
*   `interactive`: Start the guided CLI wizard (Questionary) for use in headless or terminal-only environments [REQ-INF-002].

**Note on Modalities:** CLI, Interactive, and GUI are three distinct frontends sharing a unified core. They are not mutually exclusive; the CLI is for automation, Interactive for guided terminal use, and GUI for desktop productivity.

### 3.3 Example Usage
```bash
# Export a module using a config file
doors-excel export --config my_project.json

# Validate an Excel file before importing (supports .xlsx and .xlsm)
doors-excel validate --file updates.xlsm --config mapping.json

# Import with a specific conflict policy and force purge
doors-excel import --file updates.xlsx --policy excel-overwrites --purge --force [REQ-FUN-209.1]

# Content-based import with headless conflict resolution
doors-excel import --file updates.xlsx --policy content-based --resolve-conflicts excel

# Import bypassing metadata integrity checks (High-Risk)
doors-excel import --file tampered_metadata.xlsx --ignore-integrity-check [REQ-FUN-220]

# Resume an interrupted import session from .session.json
doors-excel import --resume
```

### 3.4 CLI Visuals (Rich)
*   **Progress Bars:** Smooth, color-coded bars for batch processing [REQ-SYS-307].
*   **Tables:** Formatted tables for configuration summaries, dry-run previews [REQ-SAF-401], validation errors, and **RTF fallback summaries** [REQ-FUN-105.2].
*   **Logging:** Level-based color coding using **Loguru** and **Rich**:
    *   **DEBUG:** Grey
    *   **INFO:** Blue
    *   **NOTICE:** Bold Cyan (Icon: `🔔`) [REQ-SYS-306.2]
    *   **SUCCESS:** Green
    *   **WARNING:** Yellow
    *   **ERROR:** Red
    *   **CRITICAL:** Bold Red
    Formatting fallbacks are logged as "Warnings" in real-time.

---

## 4. Interactive CLI (Wizard)
Powered by **Questionary**, this mode guides users through complex workflows.

### 4.1 Export Workflow
1.  **Scope Selection:** Choose between "Single Module" or "Bulk Project Export" [REQ-FUN-113].
2.  **Module Selection:** Searchable list of DOORS modules/folders.
3.  **Baseline Selection:** Choose between "Current" or a list of available Baselines [REQ-FUN-102].
4.  **Attribute Selection Mode:** 
    *   "By View": Select an existing DOORS View. Attributes, filters, and sorting will be automatically identified [REQ-FUN-110, 111].
    *   "Custom": Manually pick attributes from a checklist [REQ-FUN-103].
5.  **Hierarchy & Tables:** Toggle inclusion of 'Level', 'Parent Absolute Number', and structural markers [REQ-FUN-104, 108.1].
6.  **Format Choice:** The tool uses a "Best-Effort" GitHub Flavored Markdown (GFM) approach to preserve formatting. No manual format selection is required to ensure consistency [REQ-FUN-105].
7.  **Output Path:** Specify where to save the `.xlsx` file.

### 4.2 Import Workflow
1.  **File Selection:** Select the source Excel file (.xlsx or .xlsm).
2.  **Worksheet Mapping:** For bulk files, the tool automatically matches worksheets to DOORS modules using embedded metadata (Workbook Properties) or names. Non-matching sheets are ignored [REQ-FUN-215].
3.  **Mapping Confirmation:** Review detected column-to-attribute mappings [REQ-FUN-206].
4.  **Conflict Policy:** Select (Excel Overwrites, DOORS Overwrites (Skip), Content-Based) [REQ-FUN-207].
5.  **Conflict Resolution (if Content-Based):** For any attribute-level conflicts, the user is prompted to choose the winning value (DOORS, Excel, or Manual).
6.  **Deletion Policy:** Select (Ignore, Soft-Delete, Purge) [REQ-FUN-209].
7.  **Dry-Run (Mandatory):** Display a summary of changes (New, Updated, Moved, Deleted) and check for circular links [REQ-SAF-401, REQ-FUN-214].
8.  **Confirmation:** Final "Yes/No" (with --force check for Purge) before writing to DOORS.

---

## 5. Graphical User Interface (GUI)
Built with **PySide6**, providing a professional desktop environment.

### 5.1 Main Window Layout
*   **Sidebar:** Navigation between "Export", "Import", "Configurations", and "Session History".
*   **Main Content Area:** Task-specific forms and dashboards.
*   **Status Bar:** Connection status to DOORS [REQ-SYS-301], current user, and global progress [REQ-SYS-307].

### 5.2 Export Panel
*   **Source Section:** 
    *   Module Path browser (Tree view of DOORS database).
    *   Baseline dropdown [REQ-FUN-102].
    *   Attribute Source: Toggle between "View-based" and "Manual Selection" [REQ-FUN-103, 110].
- **Options Section:**
    *   **Formatting:** Markup (GitHub Flavored Markdown (GFM)) is mandatory [REQ-FUN-105].
    *   **OLE & Images:** 
        *   "Detect OLE Objects" checkbox (adds "Has OLE" column) [REQ-FUN-106].
        *   "Use Image Placeholders" checkbox (inserts `[IMAGE: ID]`) [REQ-FUN-114].
        *   **Visual Representation:** `[IMAGE: ID]` tokens are rendered as non-editable "badges" with a lock icon.
        *   **Safety Tooltip:** *"DOORS Image: Non-syncable placeholder. Deletion in Excel may cause omission in DOORS if text is modified."*
    - **Large Content Warning [C-3]:** Automatically enabled. Attributes split into multiple columns (`_1`, `_2`) will be marked with a `[READ-ONLY: Large content detected]` note within Excel cells to discourage manual editing.
    - **Structural Protection [REQ-FUN-108.7]:**
        - **"Enable Sheet Protection"** checkbox (Locked by default if tables are detected).
        - **"Protection Password"** optional input (masked).
        - **Visual Feedback:** Structural columns (ID, Level, Object Type) are highlighted with a "padlock" icon in the UI mapping grid.
    - **Links & Tables:** Checkboxes to include/exclude Links [REQ-FUN-107] and DOORS Tables [REQ-FUN-108].
*   **Target Section:** File picker for the output Excel.
*   **Advanced Section:**
    *   "Batch Size" input for processing large modules [REQ-SYS-304].
*   **Action:** "Start Export" button with a primary color.

### 5.3 Import Panel
*   **Source Section:** Drag-and-drop area for Excel files (.xlsx, .xlsm).
*   **Validation Phase (Static):** Real-time display of Excel health [REQ-FUN-217].
    *   **Error List:** Categorized issues (Data Type Mismatch, Invalid Enum, Missing Mandatory Columns, Orphaned OLE Placeholders [REQ-FUN-217.3], **Metadata Integrity Failures [REQ-FUN-220]**). This list uses **UI virtualization** to handle thousands of potential validation errors without slowing down the application [REQ-PER-503].
    *   **Annotate Excel:** Button to append a `_DOORS_Validation_Feedback` column directly to the source file [REQ-SAF-402].
*   **Dry-Run Phase (Dynamic):** Comparative analysis with DOORS [REQ-SAF-401].
*   **Diff Engine:** Identifies changes (New, Update, Move, Delete) by comparing Excel against the live DOORS module.
*   **Metadata Health Indicator:** A "Shield" icon in the status bar indicating if the worksheet's read-only metadata is intact (Green) or tampered (Red) [REQ-FUN-220].
*   **Cascading Delete Detection:** Detects and warns about "Indirect Deletions" caused by parent purging [REQ-FUN-209.2].
*   **Formatting Alerts:** Displays a "scissors" icon next to attributes affected by a **Force-Split** [C-3.1], an info icon for RTF fallbacks [REQ-FUN-105.2], or a **"crossed-out color palette"** icon for rich format loss [REQ-FUN-105.5].
*   **OLE Review Gate:** If OLE overwrites are detected (e.g., missing placeholders), a "Review" button becomes mandatory. This opens a modal where users can **Confirm** (proceed with data loss) or **Reject** (skip the update for that attribute) each change [REQ-FUN-210.1, 210.3].
*   **Format Loss Review Gate:** If rich formatting loss is detected due to text modification, a "Review Format Loss" button becomes mandatory. This opens a modal where users must explicitly acknowledge that DOORS-specific formatting (colors, fonts) will be replaced by standard RTF rendered from Markdown [REQ-FUN-105.5].
*   **Conflict Review Gate:** In Content-Based mode, if attribute-level conflicts are detected, a "Resolve Conflicts" button becomes mandatory. This opens a modal for 3-way merge resolution [REQ-FUN-207].    *   **Link Check:** Performs directed graph analysis to detect circular link dependencies [REQ-FUN-214].
    *   **Lock Check:** Verifies if the module is editable and not locked by another user [REQ-SAF-403.1].
*   **Policies Section:** Radio buttons for Conflict [REQ-FUN-207] and Deletion [REQ-FUN-209] policies.
  *   **Conflict Options:** 
      *   **Excel Overwrites:** Force sync DOORS to Excel (ignores concurrent DOORS changes).
      *   **DOORS Overwrites (Skip):** Skip entire objects if they were modified in DOORS after export.
      *   **Content-Based:** Attribute-level 3-way merge using the Source Baseline as ancestor.
  *   **Soft-Delete Config:** Option to select which attribute (default: `Status`) will be set to `Deleted`.
*   **Preview Table:** A grid showing exactly what will change. Implements **UI virtualization** to handle up to 50,000 objects without performance degradation [REQ-PER-503].
    *   **Color-coding:** Green (New), Blue (Update), Orange (Move), Red (Delete).
    *   **Formatting Alerts:** Displays warning icons for 'RTF Fallbacks' [REQ-FUN-105.2] and 'Force-Splits' [C-3]. Hovering provides a snippet of the broken formatting or the reason for the fallback.
    *   **Structure-Wins Indicator:** Displays a "lightning bolt" icon next to objects where the table structural markers overrode the Excel `Level` column.
    *   **Exclusion Toggle:** For corrupted table blocks (Tier 2 errors), a toggle allows users to "Exclude Corrupted Tables" and proceed with the rest of the import, rather than halting the entire session.
    *   **Drill-down:** Side-by-side comparison of Current DOORS value vs. New Excel value.
*   **Action Flow:** 
    1.  "Run Validation" (Mandatory first step).
    2.  "Run Dry-Run" (Enabled only after successful validation).
    3.  "Execute Import" (Enabled only after Dry-Run is reviewed and confirmed).
    *   **Post-Execution/Failure:** If the import fails or is cancelled, a "Generate Rollback Excel" button appears prominently to allow immediate restoration of affected objects [REQ-SAF-406.1].
    *   **Purge Warning:** If a "Purge" operation was performed, the tool must explicitly state that purged objects cannot be recovered with their original Absolute Numbers and will be recreated as new objects [REQ-SAF-406.1].

### 5.4 Configuration & Templates
*   A built-in editor for JSON/YAML files [REQ-INF-003] with syntax highlighting, autocomplete for DOORS attributes, and real-time schema validation [REQ-INF-004].
*   "Templates" library for common mapping scenarios.

### 5.5 Advanced View: Table & Hierarchy Management
*   **Hierarchy Visualizer:** A side-panel showing the object tree in DOORS vs. the proposed structure from Excel. Utilizes **lazy loading** for child nodes to ensure fast initial render times for large modules (50k objects) [REQ-PER-503]. Highlights "Moved" objects [REQ-FUN-204] and placement optimizations [REQ-FUN-205].
  *   **Structure-Wins Conflict Handling:** The visualizer shall prioritize table structural markers (`TABLE_ROW`, `TABLE_CELL`) for rendering the tree. If the `Level` column in Excel contradicts this rendered position, a warning icon (!) shall be displayed next to the object with a tooltip explaining the discrepancy [REQ-FUN-108.5].
  *   **New Object Placement:** UI to map `_Parent_ID` and `_Placement` columns [REQ-FUN-203.1].
    *   **Table & Structural Logic:** 
    *   **Hybrid Preview:** The `TABLE_START` object shall display a GFM Markdown table preview in its dedicated attribute. In the UI, this is rendered as a read-only, scrollable text area to allow users to verify the table's visual layout [REQ-FUN-108.6].
    *   **Marker Management:** UI to define the "Object Type" column values for structural markers (Default: `TABLE_START`, `TABLE_ROW`, `TABLE_CELL`, `TABLE_END`, `NEW_TABLE`, `OBJECT`) [REQ-FUN-108.1].
        *   **Metadata Sync:** A toggle to "Embed Mappings in Excel" to ensure cross-user compatibility.
    *   **Table Attribute Mapping:** A dedicated grid to map table-level attributes (e.g., `tablewidth`, `border`) to Excel columns. This is separate from object-level attributes to maintain clarity [REQ-FUN-108.3].
    *   **Validation Indicator:** Real-time visual feedback for structural integrity (e.g., orphan cells, missing row containers) [REQ-FUN-108.2].
        *   **Reconciliation Feedback:** Specifically highlight objects where `Level` or `Parent Absolute Number` contradicts the table markers. Use Red highlighting for critical container mismatches that block import [REQ-FUN-108.5].
*   **Link Management Grid:** UI to review/edit link creation and deletion (DEL: prefix) [REQ-FUN-213]. Implements **UI virtualization** to manage potentially thousands of link modifications efficiently [REQ-PER-503].
    *   **Permission Logic:** The grid allows editing and deletion of **Out-links** only. **In-links** are displayed for context but are strictly read-only [REQ-FUN-107].
    *   **Format Display:** Shows links in the standardized format `[TargetID] (Type: "LinkTypeName", Mod: "LinkModuleName")` [REQ-FUN-107.1].
*   **Attribute Mapping Grid:** A searchable, filterable table to map Excel headers to DOORS attributes [REQ-FUN-206]. Implements **UI virtualization** for mapping large sets of attributes.
    *   **Placement Columns:** Configurable mapping for hierarchy fields (Default: `_Parent_ID`, `_Placement`) [REQ-FUN-203.1].
    - **Large Content Aggregation:** Multiple source columns (e.g., `Object Text_1`, `Object Text_2`, `Out-links_1`, `Out-links_2`) are displayed as a single unified field in the UI [C-3].
    - **Force-Split Indicator:** Attributes aggregated from multiple columns that suffered a "Force-Split" [C-3] are flagged with a "broken" icon, alerting the user that Excel-side formatting or parsing integrity is likely compromised.
    - **Visual Type Safety:** Status icons (Check/Warning/Error) indicating if the Excel column data type is compatible with the DOORS attribute. Exceeding 1024 chars for String types will trigger a "Blocking" error highlight.
    *   **Character Limit Warning:** For 'String' attributes, the UI shall display the character count and highlight the field in red if it exceeds the 1024-character DOORS limit [REQ-FUN-206.1].
*   **Enum Editor:** Visual selection of valid DOORS Enum values with search. Supports multi-select for Multi-value Enumerations [REQ-FUN-115].
    *   **Read-Only Protection:** System attributes (e.g., 'Created By') are greyed out and non-editable.

### 5.6 Session History & Audit Logs
*   **Searchable History Grid:** A list of all past operations (Export, Import, Validation) stored in the local SQLite database. Displays status (Success, Partial Failure, Cancelled) and timestamps.
*   **Session Details:** Selecting a session displays its configuration, logs, and a "Change Summary".
*   **Audit Trail Export:** Button to export the machine-readable JSON audit trail for any past session [REQ-SYS-306.1].
*   **Rollback Generation:** For past import sessions, a "Generate Rollback Excel" button uses the stored SQLite snapshot to create a recovery file [REQ-SAF-406.1].
*   **Log Viewer:** Integrated text viewer for detailed session logs with level-based filtering.

---

## 6. Connectivity & System Integration

### 6.1 Session Management [REQ-SYS-301]
*   **Instance Selector:** If multiple DOORS instances are running, a popup allows the user to select the target database/port.
*   **Login Overlay:** If no session is detected, a prompt asks the user to log in to DOORS first (the tool does not store credentials [REQ-SEC-701]).
*   **Version Check:** A splash screen or status indicator verifies DOORS client version (e.g., "DOORS 9.7 Detected - Compatible") [REQ-SYS-305].

### 6.2 Bulk Processing [REQ-FUN-113, 215]
*   **Multi-Module Selector:** A checklist for selecting multiple modules within a folder for bulk export to a single Excel workbook.
*   **Worksheet-to-Module Mapping:** For bulk import, a grid showing which Excel worksheet maps to which DOORS module, with "Auto-Match" based on naming.

---

## 7. Safety & Feedback Elements

### 7.1 Dry-Run Preview (The "Protection Layer")
Before any import, the UI **must** show:
*   **Summary Counters:** Total objects affected (New, Updated, Moved, Deleted, Indirect Deletions, OLE Overwrites, **Rich Format Loss**, Attribute Conflicts).
*   **Integrity Status:** A prominent warning if the **Metadata Checksum** fails, explaining that read-only fields (like Source Baseline) have been modified [REQ-FUN-220].
*   **Circular Link Warnings:** List of any detected circular dependencies that will block execution [REQ-FUN-214].
*   **Virtualized Pagination:** A scrollable grid that lazily loads records from the SQLite cache [REQ-FUN-116]. This ensures the UI remains fluid even with 50,000 diff results.
*   **DOORS Busy Overlay:** A semi-transparent overlay indicating when the DOORS client is locked during batch execution, providing clear feedback to the user and preventing accidental interaction.
*   **Critical Warnings:** 
    *   **Metadata Tamper Warning:** If checksum verification fails, the "Execute Import" button is disabled unless the user checks an "I acknowledge the risk of metadata tampering" override checkbox [REQ-FUN-220].
    *   **Cascading Delete Warning:** If a parent object is marked for "Purge" but its children are not explicitly handled in Excel, the tool shall list all affected child objects as "Indirect Deletions" [REQ-FUN-209.2].
    *   **OLE Overwrite Confirmation:** Objects with OLE overwrites (including deleted placeholders) shall be flagged in the Diff Grid with a warning icon [REQ-FUN-210.1].
        *   **Granular Control:** Users must choose to either **Confirm Overwrite** or **Discard Change** for each flagged attribute.
        *   **Discarding (Fallback):** Choosing "Discard" removes the proposed update for that specific attribute from the session, ensuring the original OLE and text remain in DOORS [REQ-FUN-210.3].
        *   **Bulk Action:** A "Review OLE Changes" button opens a modal for bulk processing. Users can "Confirm All" or "Discard All" flagged OLE changes.
        *   **Safety Gate:** The "Execute Import" button is disabled until all OLE-flagged attributes have a resolution (either Confirmed or Discarded).
    *   **Rich Format Loss Confirmation:** Objects where modified text will result in the loss of original rich formatting (colors, fonts) shall be flagged in the Diff Grid with a **"crossed-out color palette"** icon [REQ-FUN-105.5].
        *   **Granular Control:** Users must choose to either **Confirm Format Loss** or **Discard Change** for each flagged attribute.
        *   **Safety Gate:** The "Execute Import" button is disabled until all Format Loss flags have a resolution.
        *   **Bulk Action:** A "Review Format Loss" button opens a modal for bulk processing.
    *   **Conflict Resolution (3-Way Merge):** Conflicting attributes (modified in both DOORS and Excel) shall be flagged with a "Conflict" icon [REQ-FUN-207].
        *   **Granular Control:** Users must choose between **DOORS Value**, **Excel Value**, or a **Manual Merge** (via a side-by-side text editor) for each conflict.
        *   **Safety Gate:** In Content-Based mode, the "Execute Import" button is disabled until all attribute conflicts have been resolved.
    *   "Baseline Mismatch": If the Excel "Source Baseline" is outdated [REQ-FUN-208].
    *   "Lock Failure": Displays the username of the person currently editing the module [REQ-SAF-403.1].
*   **Purge Safeguard:** If "Purge" is selected, a high-contrast modal requires the user to type "PURGE" or "DELETE" to confirm the action [REQ-FUN-209.1].

### 7.2 Progress Tracking & Session Recovery [REQ-SYS-307, REQ-SAF-405]
*   **Global Progress:** Overall percentage of the task.
* **Detailed Log:** Scrolling log of current activity, referencing objects by their **Absolute Number**.
* **Dry-Run Progress:** A dedicated progress indicator for the diffing process, including an "Abort" option to safely cancel the pre-calculation.
* **Batching Status:** Indicator showing current DXL chunking progress.
* **Keep-Alive Heartbeat:** A subtle "heartbeat" icon or status text in the status bar (e.g., "Session Active 💓") to indicate the background keep-alive mechanism is functioning during long-running tasks [REQ-SYS-308].
* **Session Recovery (Resume):** 
    * **Detection:** Upon startup, if the tool detects a `.session.json` state file, a notification bar will appear: *"An incomplete session was detected. Would you like to resume?"*.
    *   **Action:** 
        *   **Resume:** Clicking "Resume" will re-validate the environment and restart the process from the last successfully processed object. 
        *   **Rollback:** A "Generate Rollback Excel" option is provided to recover from the partial import instead of resuming [REQ-SAF-406.1].
        *   **Dismiss:** Clear the recovery state and start fresh.
    *   **Visual Feedback:** During a resumed process, the progress bar will highlight the previously completed section in a different shade.

### 7.3 Formatting & Integrity Reporting
*   **RTF Fallback Warnings:** A dedicated report section and log entries for objects where RTF-to-Markdown conversion fell back to plain text. Each entry shall explicitly reference the **Absolute Number** and the identified **unsupported RTF element/structure** (e.g., "Nested table", "Unsupported control word") to ensure transparency and traceability [REQ-FUN-105.2].
*   **Force-Split Warnings:** A specific section in the report for attributes exceeding the 32k Excel limit that could not be split at a structural boundary [C-3]. These are flagged as "Integrity Risks" because the structural integrity (Markdown or link entries) is broken across cells, making Excel-side formatting or parsing likely compromised.
*   **Line-by-Line Validation:** A "Problem List" at the bottom of the GUI showing exactly which Excel rows have issues. This list uses **UI virtualization** to handle thousands of potential validation errors without slowing down the application [REQ-PER-503].
*   **Validation Results Column:** Option to automatically append a `_DOORS_Validation_Feedback` column directly to the source Excel file for offline correction. The tool will automatically clear existing content in this column at the start of a new run to prevent pollution [REQ-SAF-402].
*   **Change Summary (Audit Log):** Button to export the session's machine-readable change summary (JSON) [REQ-SYS-306.1]. These summaries are persisted and can also be retrieved via the **Session History** view.

---

## 8. Visual Design Principles
*   **Theme:** Professional "Enterprise" look. Support for Light and Dark modes.
*   **Typography:** Clear, monospaced fonts (e.g., JetBrains Mono) for IDs and DXL logs; Sans-serif (e.g., Inter/Segoe UI) for UI labels.
*   **Icons:** Material Design icons for actions (Export, Import, Save, Refresh).
*   **Color Palette:**
    *   **Success:** Emerald Green (#10B981).
    *   **Warning:** Amber (#F59E0B).
    *   **Error:** Crimson (#EF4444).
    *   **Primary Action:** Cobalt Blue (#2563EB).

---

## 9. Interaction States
*   **Idle:** Connection status shown; forms ready for input.
*   **Validating:** Spinners shown; inputs disabled to prevent state change.
*   **Processing:** Progress bars active; "Cancel" button available for graceful termination and state saving [REQ-SAF-405].
*   **Completed:** Success/Failure summary; "Open Log", "Open Resulting File", and "Open DOORS Module" shortcuts.
Resulting File", and "Open DOORS Module" shortcuts.
