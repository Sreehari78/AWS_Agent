# Data Directory

This directory contains persistent data files used by the EKS Upgrade Agent.

## Structure

```
data/
├── progress/           # Upgrade progress tracking files
│   └── upgrade_*.json  # Individual upgrade progress files
└── README.md          # This file
```

## Progress Files

Progress files are stored as JSON documents with the naming pattern:

- `upgrade_{upgrade_id}.json`

Each file contains:

- Upgrade metadata (ID, cluster name, status, timing)
- Task details with status, duration, and event history
- Error information and retry tracking
- Complete audit trail for compliance and debugging

## Future Extensions

This directory structure is designed to accommodate additional data types:

- Configuration files
- Cache data
- Temporary processing files
- Export/import data

## Usage

The storage path should be configured to point to this `data` directory, and the system will automatically create the appropriate subdirectories as needed.
