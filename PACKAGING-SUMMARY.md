# BlueBubbles Client - Flatpak & Packaging Setup

## What Was Done

### 🐧 Flatpak Support Added

1. **Flatpak Manifest**: `com.github.bluebubbles.client.yml`
   - Configured for GNOME 47 runtime
   - Includes all Python dependencies
   - Proper sandboxing with necessary permissions
   - Network, IPC, and filesystem access as needed

2. **Application Metadata**:
   - `com.github.bluebubbles.client.desktop` - Desktop entry file
   - `com.github.bluebubbles.client.metainfo.xml` - AppStream metadata
   - Application icon in SVG format

### 📦 Package Building Infrastructure

3. **Python Packaging**:
   - `setup.py` - Complete Python package configuration
   - `MANIFEST.in` - File inclusion rules
   - `LICENSE` - MIT license file
   - Updated `main.py` with better CLI support

4. **GitHub Actions Workflows**:
   - `.github/workflows/build-packages.yml` - Builds DEB, RPM, and TAR packages
   - `.github/workflows/flatpak.yml` - Builds Flatpak packages
   - Nightly builds scheduled daily at 2 AM UTC
   - Manual trigger support for testing

### 🔧 Build Tools

5. **Local Testing**:
   - `test-packaging.sh` - Comprehensive packaging test script
   - `BUILD.md` - Detailed build instructions
   - Updated `.gitignore` for package artifacts

6. **Documentation**:
   - Comprehensive README with installation instructions
   - Build documentation with troubleshooting
   - Project structure documentation

## Package Formats Supported

### 🐧 Flatpak
- **File**: `bluebubbles-client.flatpak`
- **Installation**: `flatpak install --user bluebubbles-client.flatpak`
- **Best for**: Universal Linux, sandboxed installation

### 📦 DEB Package
- **File**: `bluebubbles-client_*.deb`
- **Installation**: `sudo dpkg -i bluebubbles-client_*.deb`
- **Best for**: Ubuntu, Debian, and derivatives

### 🔴 RPM Package
- **File**: `bluebubbles-client-*.rpm`
- **Installation**: `sudo rpm -i bluebubbles-client-*.rpm`
- **Best for**: Fedora, RHEL, CentOS, SUSE

### 📄 TAR Package
- **File**: `bluebubbles-client-*.tar.gz`
- **Installation**: Extract and run `sudo ./install.sh`
- **Best for**: Any Linux distribution, manual installation

## Automated Builds

### Nightly Releases
- Triggered daily at 2 AM UTC
- Creates pre-release with all package formats
- Version format: `1.0.0-nightly.YYYYMMDD.HHMMSS`

### Development Builds
- Triggered on every push to main/develop
- Builds all package formats as artifacts
- Version format: `1.0.0-dev.YYYYMMDD.HHMMSS`

### Manual Builds
- Can be triggered from GitHub Actions tab
- Select workflow and click "Run workflow"
- Useful for testing changes before merge

## Application Improvements

### Enhanced CLI Support
- `--help` flag shows usage information
- `--version` flag shows version information
- Better module path handling for installed packages

### Proper Application ID
- Uses reverse domain notation: `com.github.bluebubbles.client`
- Consistent across all package formats
- Follows Linux desktop standards

### Icon and Branding
- Custom SVG icon with BlueBubbles theme
- Proper desktop integration
- AppStream metadata for software centers

## Testing

Run the packaging test suite:
```bash
./test-packaging.sh
```

This validates:
- Python syntax and dependencies
- Package building process
- Desktop file validation
- Application startup
- Flatpak manifest syntax

## Next Steps

1. **Push to GitHub**: All files are ready for version control
2. **Test Workflows**: GitHub Actions will automatically build packages
3. **Create Release**: Tag a release to generate stable packages
4. **Submit to Flathub**: Consider submitting to official Flatpak repository
5. **Package Repositories**: Consider submitting to distribution repositories

## File Summary

### New Files Created:
- `com.github.bluebubbles.client.yml` - Flatpak manifest
- `com.github.bluebubbles.client.desktop` - Desktop entry
- `com.github.bluebubbles.client.metainfo.xml` - AppStream metadata
- `setup.py` - Python packaging configuration
- `MANIFEST.in` - Package file inclusion rules
- `LICENSE` - MIT license
- `test-packaging.sh` - Local testing script
- `BUILD.md` - Build documentation
- `.github/workflows/build-packages.yml` - Package build workflow
- `.github/workflows/flatpak.yml` - Flatpak build workflow
- `icons/com.github.bluebubbles.client.svg` - Application icon

### Modified Files:
- `main.py` - Enhanced CLI support and module loading
- `README.md` - Comprehensive documentation
- `.gitignore` - Added package artifacts

## Ready for Production

The BlueBubbles client is now fully prepared for:
- ✅ Flatpak distribution
- ✅ Traditional Linux package managers
- ✅ Automated nightly builds
- ✅ Professional Linux desktop integration
- ✅ Easy installation across all major Linux distributions

All package formats follow Linux desktop standards and best practices for security, installation, and user experience.
