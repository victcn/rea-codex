# Contributing & Reproduction Guide

## Workflow Commands

1. **Extract Core Artifacts & Embedded Assets from Local Binary**:
   ```bash
   npm run extract
   ```
2. **Extract Deep Components (Syntect, V8 Snapshot, DWARF, Git Forks, Plugins)**:
   ```bash
   npm run extract-deep
   ```
3. **Build Bidirectional Binary Virtual Address <-> Rust Source Map**:
   ```bash
   npm run map-addresses
   ```
4. **Inspect Binary Assets or Resolve Stripped Function Address (`0x...`)**:
   ```bash
   npm run inspect -- --addr 0x1a08d90
   ```
5. **Run Repository Analyzer**:
   ```bash
   npm run analyze-repo
   ```
6. **Run the Automated 19-Point Self-Test Suite**:
   ```bash
   npm test
   ```
7. **Run in Pure Local Isolated Environment (`.isolated-env`)**:
   ```bash
   npm run isolated -- features list
   ```
