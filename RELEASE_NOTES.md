# Release Notes: Google Tasks Backend Support

## Version: Multi-Backend Support (Phase 1-6 Complete)

### Release Date
January 2026

### Overview
This release adds comprehensive Google Tasks backend support alongside the existing Microsoft To Do integration, enabling users to choose their preferred task management service while maintaining full bidirectional sync with orgplan markdown files.

## 🎉 New Features

### Google Tasks Backend
- **OAuth 2.0 Authentication**: Interactive browser-based login with automatic token refresh
- **Task Synchronization**: Full bidirectional sync between orgplan and Google Tasks
- **Primary List Support**: Automatically uses primary task list if no list specified
- **Token Management**: Secure token storage in `.tokens/google_tokens.json`
- **Task Notes**: Sync task body/notes between systems
- **Completion Status**: Bidirectional status sync (DONE ↔ Completed)
- **Due Dates**: Bidirectional due date sync using orgplan timestamp markers (e.g., `DEADLINE: <YYYY-MM-DD>` or `<YYYY-MM-DD>`)

### Multi-Backend Architecture
- **Pluggable Backend System**: Clean abstraction layer supporting multiple backends
- **Backend Factory**: Easy instantiation with `create_backend()`
- **Multiple ID Markers**: Tasks can have both `ms-todo-id` and `google-tasks-id`
- **Backend Isolation**: Each backend operates independently on its own markers
- **Dynamic Backend Selection**: Choose backend via config or CLI

### Configuration Enhancements
- **TASK_BACKEND** environment variable for default backend selection
- **Google-specific** configuration options (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
- **Backend override** via `--backend` CLI argument
- **Unified configuration** system supporting both backends

## 📋 Feature Comparison

| Feature | Microsoft To Do | Google Tasks |
|---------|----------------|--------------|
| Authentication | Application or Delegated (MSAL) | OAuth 2.0 (User consent) |
| Priority Support | ✅ High/Normal/Low | ❌ Not supported |
| Task Notes | ✅ Synced | ✅ Synced |
| Completion Status | ✅ Synced | ✅ Synced |
| Multiple Lists | ✅ Supported | ✅ Supported |
| Default List | Must specify | Primary list auto-used |
| Admin Consent | Required (app mode) | Not required |
| Cron Support | ✅ Yes | ✅ Yes |

## 🔧 Technical Improvements

### Code Quality
- **Black formatting**: All Python code formatted for consistency
- **Type hints**: Enhanced type annotations throughout codebase
- **Abstract base classes**: TaskBackend and TaskItem for clean interfaces
- **Error handling**: Backend-specific error conversion and retry logic

### Testing
- **Unit tests**: Comprehensive test coverage for Google Tasks backend
- **Multi-backend tests**: Tests for backend switching and multiple ID markers
- **Manual test checklist**: Detailed testing scenarios for validation
- **Integration tests**: Framework for testing with real APIs (optional)

### Documentation
- **README.md**: Completely updated with backend-agnostic content
- **GOOGLE_TASKS_SETUP.md**: Complete OAuth 2.0 setup guide
- **BACKEND_MIGRATION.md**: Guide for switching between backends
- **ARCHITECTURE.md**: Technical documentation of multi-backend design
- **TROUBLESHOOTING.md**: Updated with Google Tasks troubleshooting
- **WORKFLOWS.md**: Backend-specific workflow examples

## 🚀 Usage Examples

### Google Tasks - Basic Sync
```bash
# First time (interactive auth)
python tools/sync.py --backend google --todo-list "My Tasks"

# Subsequent runs (uses cached tokens)
python tools/sync.py --backend google
```

### Microsoft To Do - Existing Workflow
```bash
# Application mode (unchanged)
python tools/sync.py --todo-list "Orgplan 2025"

# Delegated mode (unchanged)
python tools/sync.py --todo-list "Orgplan 2025" --auth-mode delegated
```

### Switching Backends
```bash
# Sync to Microsoft
python tools/sync.py --todo-list "Orgplan 2025"

# Sync same tasks to Google
python tools/sync.py --backend google --todo-list "Orgplan 2025"

# Tasks now have both ID markers
```

## 📝 Migration Guide

### From Microsoft To Do to Google Tasks
1. Set up Google OAuth credentials (see GOOGLE_TASKS_SETUP.md)
2. Add credentials to .env file
3. Run first Google sync: `python tools/sync.py --backend google --todo-list "My Tasks"`
4. Tasks will get `google-tasks-id` markers alongside existing `ms-todo-id`
5. Update .env: `TASK_BACKEND=google`
6. Update cron jobs if using automation

See [BACKEND_MIGRATION.md](docs/BACKEND_MIGRATION.md) for detailed migration instructions.

## ⚠️ Breaking Changes

**None** - This release is fully backward compatible with existing Microsoft To Do setups.

## 🐛 Known Issues

### Google Tasks Limitations
- **No priority support**: Priority tags (#p1, #p2, #p3) are ignored when using Google Tasks
- **No subtasks**: Google Tasks subtasks are not currently synced (future enhancement)

### General
- Very long task titles (>255 chars) may be truncated
- Task deletions are not synced (by design)
- Only one monthly file processed at a time

## 🔮 Future Enhancements

### Planned Features
- Subtasks/checklist items support
- Additional backends (Todoist, Trello, Notion)
- Real-time sync via webhooks
- Conflict resolution UI

### Performance
- Parallel API calls for faster sync
- Incremental sync (delta changes only)
- Pagination for very large task lists (>1000 tasks)

## 📚 Documentation

### New Documentation
- [Google Tasks Setup Guide](docs/GOOGLE_TASKS_SETUP.md)
- [Backend Migration Guide](docs/BACKEND_MIGRATION.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)

### Updated Documentation
- [README.md](README.md) - Backend-agnostic content
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Google Tasks issues
- [Example Workflows](docs/WORKFLOWS.md) - Backend-specific examples

## 🙏 Acknowledgments

This release implements a comprehensive multi-backend architecture designed for extensibility and maintainability. Special attention was paid to:
- Maintaining backward compatibility
- Clean separation of concerns
- Comprehensive documentation
- Extensive testing coverage

## 📞 Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/mlrdevgit/orgplan-todo/issues
- Documentation: See docs/ directory
- Troubleshooting: See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## 📄 License

[Add license information]

---

**Full Changelog**: Phases 1-6 implementing complete Google Tasks backend support with multi-backend architecture
