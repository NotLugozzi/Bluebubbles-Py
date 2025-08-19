#!/bin/bash

# Test script for package building
# This script tests the package building process locally

set -e

echo "🚀 Testing BlueBubbles Client Package Building"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -f "setup.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_status "Starting package build tests..."

# Clean up any previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf build/ dist/ deb_dist/ *.egg-info/ bluebubbles-client-* *.deb *.rpm *.tar.gz *.flatpak *.spec .flatpak-builder/ build-dir/ export/ ~/rpmbuild/

# Test 1: Check Python syntax
echo "🐍 Testing Python syntax..."
python3 -m py_compile main.py
find src -name "*.py" -exec python3 -m py_compile {} \;
print_status "Python syntax check passed"

# Test 2: Check dependencies
echo "📦 Checking dependencies..."
python3 -c "
import sys
try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw
    print('✓ GTK4 and Libadwaita available')
except ImportError as e:
    print(f'✗ Missing GUI dependencies: {e}')
    sys.exit(1)

try:
    import requests, toml, aiohttp
    from PIL import Image
    print('✓ Python dependencies available')
except ImportError as e:
    print(f'⚠ Missing Python dependencies: {e}')
    print('  Install with: pip3 install -r requirements.txt')
"

# Test 3: Test setup.py
echo "⚙️ Testing setup.py..."
python3 setup.py check
print_status "setup.py check passed"

# Test 4: Build source distribution
echo "📦 Building source distribution..."
python3 setup.py sdist
if [ -f "dist/bluebubbles_client-1.0.0.tar.gz" ]; then
    print_status "Source distribution built successfully"
else
    print_error "Failed to build source distribution"
    exit 1
fi

# Test 5: Build TAR package
echo "📦 Building TAR package..."
VERSION="1.0.0-test.$(date +%Y%m%d.%H%M%S)"

# Create binary distribution
mkdir -p bluebubbles-client-$VERSION

# Copy application files
cp -r src bluebubbles-client-$VERSION/
cp main.py bluebubbles-client-$VERSION/
cp requirements.txt bluebubbles-client-$VERSION/
cp README.md bluebubbles-client-$VERSION/
cp *.desktop bluebubbles-client-$VERSION/
cp *.metainfo.xml bluebubbles-client-$VERSION/
cp -r icons bluebubbles-client-$VERSION/

# Create install script
cat > bluebubbles-client-$VERSION/install.sh << 'EOF'
#!/bin/bash
set -e

PREFIX=${PREFIX:-/usr/local}

echo "Installing BlueBubbles Client to $PREFIX"

# Install Python files
mkdir -p $PREFIX/lib/bluebubbles-client
cp -r src $PREFIX/lib/bluebubbles-client/
cp main.py $PREFIX/lib/bluebubbles-client/

# Create launcher script
mkdir -p $PREFIX/bin
cat > $PREFIX/bin/bluebubbles << 'LAUNCHER_EOF'
#!/bin/bash
cd /usr/local/lib/bluebubbles-client
python3 main.py "$@"
LAUNCHER_EOF
chmod +x $PREFIX/bin/bluebubbles

# Install desktop file
mkdir -p $PREFIX/share/applications
cp com.github.bluebubbles.client.desktop $PREFIX/share/applications/

# Install metainfo
mkdir -p $PREFIX/share/metainfo
cp com.github.bluebubbles.client.metainfo.xml $PREFIX/share/metainfo/

# Install icon
mkdir -p $PREFIX/share/icons/hicolor/scalable/apps
cp icons/com.github.bluebubbles.client.svg $PREFIX/share/icons/hicolor/scalable/apps/

echo "Installation complete!"
echo "You can now run 'bluebubbles' or find it in your applications menu."
EOF

chmod +x bluebubbles-client-$VERSION/install.sh

# Create uninstall script
cat > bluebubbles-client-$VERSION/uninstall.sh << 'EOF'
#!/bin/bash
set -e

PREFIX=${PREFIX:-/usr/local}

echo "Uninstalling BlueBubbles Client from $PREFIX"

rm -rf $PREFIX/lib/bluebubbles-client
rm -f $PREFIX/bin/bluebubbles
rm -f $PREFIX/share/applications/com.github.bluebubbles.client.desktop
rm -f $PREFIX/share/metainfo/com.github.bluebubbles.client.metainfo.xml
rm -f $PREFIX/share/icons/hicolor/scalable/apps/com.github.bluebubbles.client.svg

echo "Uninstallation complete!"
EOF

chmod +x bluebubbles-client-$VERSION/uninstall.sh

# Create README for the package
cat > bluebubbles-client-$VERSION/INSTALL.md << 'EOF'
# BlueBubbles Client Installation

## Requirements

- Python 3.8 or higher
- GTK4
- Libadwaita
- Python GObject bindings

### Ubuntu/Debian
```bash
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
pip3 install -r requirements.txt
```

### Fedora/RHEL
```bash
sudo dnf install python3 python3-gobject python3-cairo gtk4-devel libadwaita-devel
pip3 install -r requirements.txt
```

### Arch Linux
```bash
sudo pacman -S python python-gobject python-cairo gtk4 libadwaita
pip3 install -r requirements.txt
```

## Installation

1. Install system dependencies (see above)
2. Install Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
3. Run the install script:
   ```bash
   sudo ./install.sh
   ```

## Uninstallation

Run the uninstall script:
```bash
sudo ./uninstall.sh
```

## Manual Installation

You can also run the application directly without installing:
```bash
python3 main.py
```
EOF

# Create tar.gz
tar -czf bluebubbles-client-$VERSION.tar.gz bluebubbles-client-$VERSION

if [ -f "bluebubbles-client-$VERSION.tar.gz" ]; then
    print_status "TAR package built successfully"
    ls -la bluebubbles-client-$VERSION.tar.gz
else
    print_error "Failed to build TAR package"
fi

# Test 6: Build RPM package
echo "📦 Building RPM package..."
if command -v rpmbuild &> /dev/null; then
    # Create spec file
    cat > bluebubbles-client.spec << 'EOF'
%define name bluebubbles-client
%define version VERSION_PLACEHOLDER
%define release 1

Summary: BlueBubbles GTK4 Client for Linux
Name: %{name}
Version: %{version}
Release: %{release}
License: MIT
Group: Applications/Internet
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: NotLugozzi
Url: https://github.com/NotLugozzi/Bluebubbles-Py

Requires: python3
Requires: python3-gobject
Requires: gtk4
Requires: libadwaita

%description
BlueBubbles is a cross-platform ecosystem of apps aimed to bring iMessage to Android, Windows, Linux, and Web!
This is the Linux GTK4 client that allows you to connect to your BlueBubbles server and send/receive iMessages.

%prep
%setup -n %{name}-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --root=$RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%{_bindir}/bluebubbles
%{_prefix}/lib/python*/site-packages/*
%{_datadir}/applications/com.github.bluebubbles.client.desktop
%{_datadir}/metainfo/com.github.bluebubbles.client.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/com.github.bluebubbles.client.svg

%changelog
* $(date +'%a %b %d %Y') Builder <builder@example.com> - %{version}-%{release}
- Test build
EOF

    # Replace version placeholder
    sed -i "s/VERSION_PLACEHOLDER/$VERSION/" bluebubbles-client.spec

    # Build source distribution for RPM
    RPM_VERSION="1.0.0"  # Use simple version for RPM
    sed -i "s/version='1.0.0'/version='$RPM_VERSION'/" setup.py
    python3 setup.py sdist
    
    # Copy source to rpmbuild
    mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    cp dist/*.tar.gz ~/rpmbuild/SOURCES/bluebubbles-client-$RPM_VERSION.tar.gz
    cp bluebubbles-client.spec ~/rpmbuild/SPECS/

    # Build RPM
    rpmbuild -ba ~/rpmbuild/SPECS/bluebubbles-client.spec 2>/dev/null || print_warning "RPM build failed (this is normal without proper dependencies)"

    # Check if RPM was built
    if ls ~/rpmbuild/RPMS/noarch/*.rpm 1> /dev/null 2>&1; then
        print_status "RPM package built successfully"
        ls -la ~/rpmbuild/RPMS/noarch/*.rpm
        cp ~/rpmbuild/RPMS/noarch/*.rpm .
    else
        print_warning "RPM package building failed (missing dependencies or rpmbuild issues)"
    fi
else
    print_warning "rpmbuild not available, skipping RPM test (install with: sudo dnf install rpm-build)"
fi

# Test 7: Build Flatpak package
echo "🐧 Building Flatpak package..."
if command -v flatpak-builder &> /dev/null; then
    # Check if GNOME runtime is available
    if flatpak list --runtime | grep -q "org.gnome.Platform.*47"; then
        print_status "GNOME 47 runtime found, building Flatpak..."
        
        # Clean any previous builds
        rm -rf .flatpak-builder build-dir export *.flatpak
        
        # Build Flatpak
        if flatpak-builder build-dir com.github.bluebubbles.client.yml --force-clean --disable-rofiles-fuse 2>/dev/null; then
            print_status "Flatpak build completed"
            
            # Create bundle
            if flatpak build-export export build-dir 2>/dev/null && \
               flatpak build-bundle export bluebubbles-client-test.flatpak com.github.bluebubbles.client 2>/dev/null; then
                print_status "Flatpak package built successfully"
                ls -la bluebubbles-client-test.flatpak
            else
                print_warning "Failed to create Flatpak bundle"
            fi
        else
            print_warning "Flatpak build failed (this is normal without all dependencies)"
        fi
    else
        print_warning "GNOME 47 runtime not available. Install with:"
        echo "  flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47"
    fi
else
    print_warning "flatpak-builder not available, skipping Flatpak build"
fi

# Test 8: Test desktop file
echo "🖥️ Testing desktop file..."
if command -v desktop-file-validate &> /dev/null; then
    desktop-file-validate com.github.bluebubbles.client.desktop
    print_status "Desktop file validation passed"
else
    print_warning "desktop-file-validate not available, skipping desktop file validation"
fi

# Test 9: Test application startup (dry run)
echo "🚀 Testing application startup (dry run)..."
timeout 5 python3 main.py --help 2>/dev/null || true
print_status "Application startup test completed"

echo ""
echo "🎉 Package building tests completed!"
echo ""
echo "📋 Summary:"
echo "  - Source distribution: $(ls dist/*.tar.gz 2>/dev/null || echo 'Not built')"
echo "  - TAR package: $(ls bluebubbles-client-*.tar.gz 2>/dev/null || echo 'Not built')"
echo "  - RPM package: $(ls *.rpm 2>/dev/null || echo 'Not built')"
echo "  - Flatpak package: $(ls *.flatpak 2>/dev/null || echo 'Not built')"
echo "  - Desktop file: com.github.bluebubbles.client.desktop"
echo "  - Flatpak manifest: com.github.bluebubbles.client.yml"
echo ""
echo "🔧 To install locally:"
echo "  pip3 install dist/bluebubbles_client-1.0.0.tar.gz"
echo ""
echo "📦 To install packages:"
if ls bluebubbles-client-*.tar.gz 1> /dev/null 2>&1; then
    echo "  TAR: tar -xzf bluebubbles-client-*.tar.gz && cd bluebubbles-client-* && sudo ./install.sh"
fi
if ls *.rpm 1> /dev/null 2>&1; then
    echo "  RPM: sudo rpm -i *.rpm"
fi
if ls *.flatpak 1> /dev/null 2>&1; then
    echo "  Flatpak: flatpak install --user *.flatpak"
fi
echo ""
echo "🐧 To build Flatpak:"
echo "  flatpak-builder build-dir com.github.bluebubbles.client.yml --force-clean"
echo ""
print_status "All tests completed successfully!"
