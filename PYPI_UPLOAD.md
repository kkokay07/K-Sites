# PyPI Upload Script for K-Sites

This document outlines the complete process for uploading the K-Sites package to PyPI.

## Package Information

**Package Name**: k-sites
**Version**: 1.0.0
**Description**: Universal K-Sites: AI-Powered CRISPR Guide RNA Design Platform with Pathway-Aware Off-Target Filtering

## Developers
- Kanaka KK (Lead Architect)
- Sandip Garai (Neo4j Graph Integration Specialist)
- Jeevan C (CRISPR Algorithm Developer)
- Tanzil Fatima (Bioinformatics Analyst)

## Upload Process

1. **Prepare the environment**:
   ```bash
   pip install twine
   ```

2. **Build the package** (already done):
   ```bash
   python -m build
   ```
   
   This creates:
   - `dist/k_sites-1.0.0.tar.gz` (source distribution)
   - `dist/k_sites-1.0.0-py3-none-any.whl` (wheel distribution)

3. **Upload to Test PyPI first** (recommended):
   ```bash
   twine upload --repository testpypi dist/*
   ```

4. **Upload to PyPI**:
   ```bash
   twine upload dist/*
   ```

## Verification

After upload, the package will be available at:
- https://pypi.org/project/k-sites/

Users will be able to install with:
```bash
pip install k-sites
```

## Documentation

All documentation is included in the package:
- README.md (included in long_description)
- All module docstrings
- CLI help text
- Configuration examples

## Package Contents

The package includes:
- All Python modules in the k_sites/ directory
- Command-line interface with 'k-sites' entry point
- Complete documentation
- Test files
- Configuration examples

## Dependencies

Automatically installed with the package:
- requests>=2.25.0
- biopython>=1.78
- neo4j>=4.4.0
- pyyaml>=5.4.0
- tqdm>=4.60.0
- dataclasses-json>=0.5.0
- pandas>=1.3.0

## License

MIT License - see LICENSE file in the package.

## Post-Upload Verification

After uploading, verify the package works:

```bash
# Create a new environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install the package
pip install k-sites

# Verify installation
k-sites --help
```

## Repository

The complete source code is available at:
https://github.com/KanakaKK/K-sites

This includes:
- Full source code
- Documentation
- Tests
- Examples
- Configuration templates