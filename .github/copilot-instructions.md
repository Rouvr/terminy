# Terminy AI Coding Instructions

## Architecture Overview

Terminy is a **PySide6-based desktop application** for managing records in a hierarchical directory structure with advanced search capabilities. It follows a clean separation between GUI (`src/gui/`) and logic (`src/logic/`) layers.

### Core Components

- **Controller** (`src/logic/controller.py`): Central state manager handling navigation, data persistence, and business logic
- **Storage** (`src/logic/storage.py`): JSON-based persistence with backup/versioning for `data.json`, `config.json`, and `recycle_bin.json`
- **RecordIndexer** (`src/logic/indexer.py`): Performance-critical component using `marisa-trie` and `RapidFuzz` for full-text search
- **MainWindow** (`src/gui/main_window.py`): Primary GUI orchestrator connecting widgets and handling signals

### Data Model

- **FileObject**: Base class with normalized text fields (`_normal_name`, `_normal_file_name`) for search optimization
- **Directory**: Hierarchical container with parent/child relationships
- **Record**: Main data entity with validity dates, tags, and configurable visible attributes

## Development Patterns

### Logging Convention
Every module uses the **same logging pattern**:
```python
import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)  # or logging.INFO
```
Always use timestamped debug messages: `logger.debug(f"[ModuleName][{datetime.now()}] Message")`

### Signal-Slot Architecture
GUI components communicate via **PySide6 signals**. Example pattern from `DirectoryTree`:
```python
directoryClicked = Signal(Directory)
directoryDoubleClicked = Signal(Directory)
directoryRightClicked = Signal(Directory, QPoint)
```

### Normalization Strategy
Text search relies on **Unidecode normalization** (`src/logic/helpers.py`). All searchable text fields have corresponding `_normal_*` counterparts automatically maintained.

### Widget Organization
- **Widgets** in `src/gui/widgets/`: Reusable UI components with specific responsibilities
- **Main GUI modules** in `src/gui/`: Higher-level orchestration and models
- **CenterScrollPage**: Container managing the main content panes with scroll behavior

## Critical Workflows

### Running the Application
```bash
python -m src.terminy  # Entry point sets Czech locale by default
```

### Navigation System
- **Top Bar Navigation**: Back/Forward/Up/Home buttons for directory navigation
- **Home Button**: Always returns to root directory (`_navigate_home()`)
- **Left Panel Navigation**: 
  - Clicking "Workspace" navigates to root directory
  - Clicking "Recycle Bin" navigates to recycle bin
  - Directory tree items navigate to specific directories

### Data Persistence
- **Auto-backup**: Storage creates `.old` files before overwriting
- **Data paths**: Managed via `PathManager` or explicit constructor args
- **Config management**: Favorites and UI settings stored in `config.json`

### Search Implementation
The `RecordIndexer` builds multiple **marisa-trie** indexes on normalized fields (name, filename, description, ID). Search queries use fuzzy matching via `RapidFuzz` with configurable thresholds.

### Internationalization
- Language files in `src/gui/lang/` (currently `cs.py`, `cs.txt`, `en_en.txt`)
- `Language.get("KEY")` for translated strings
- Registry-based locale persistence

## Key Integration Points

### Controller-GUI Communication
The `Controller` is injected into GUI components and provides the **single source of truth** for:
- Current directory navigation (`get_current_directory()`, `navigate_to()`)
- Record filtering and search (`search()`, `get_current_record_list()`)
- Favorites management (`add_favorite()`, `get_favorites()`)

### File Path Resolution
Use `Controller.object_to_path()` and `Controller.path_to_object()` for converting between file objects and serializable path representations.

### Custom Widget Integration
When adding new widgets, follow the pattern:
1. Create in `src/gui/widgets/`
2. Add signal definitions
3. Connect to controller in `MainWindow._connect_signals()`
4. Handle page scroll mode if applicable

## Testing & Debugging

- Test files exist in `src/logic/` (e.g., `test_serialization.py`, `test.py`)
- Use the rotating log file `terminy.log` for debugging
- Controller state can be inspected via `dir_history` and `current_dir` properties

## Dependencies to Understand

- **PySide6**: All GUI components, signals/slots, and styling
- **marisa-trie**: Memory-efficient prefix tree for search indexing
- **RapidFuzz**: Fast fuzzy string matching for search queries
- **Unidecode**: Text normalization for search and indexing

## Common Anti-Patterns to Avoid

- **Don't bypass the Controller**: Always use controller methods for data access and navigation
- **Don't hardcode paths**: Use `PathManager` or constructor arguments for data locations
- **Don't skip normalization**: Ensure all searchable text goes through `normalize()` function
- **Don't ignore logging**: Follow the established logging pattern for debugging support