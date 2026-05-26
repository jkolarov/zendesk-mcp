# Zendesk MCP — Documentation

**Version:** 0.1.0  
**Repository:** https://github.com/jkolarov/zendesk-mcp  
**Tested against:** freelancer-17746.zendesk.com  
**Last test date:** 2026-05-27  
**Tools registered:** 30

---

## What is this?

An unofficial [Model Context Protocol](https://modelcontextprotocol.io) server that gives AI assistants (Claude, Cursor, Amazon Q) full read/write access to Zendesk via natural language.

Once installed, you can ask Claude things like:
- *"How many open tickets do we have assigned to John?"*
- *"Show me ticket #1042 with all its comments"*
- *"Edit ticket #55 — set priority to urgent and add tag escalated"*
- *"List all active triggers that mention SLA"*
- *"What views are available in our Zendesk?"*

## Pages in this folder

| Page | Contents |
|---|---|
| Architecture | Code structure, auth flow, security design, data model |
| Tool Reference | All 30 tools — purpose, inputs, outputs, examples |
| Test Results | Live test runs against test env, all tools verified |
| Possible Improvements | Open ideas and future enhancements |
