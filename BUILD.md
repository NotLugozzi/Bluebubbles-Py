# Building BlueBubbles Client Packages

This document describes how to build various package formats for BlueBubbles Client.

## Prerequisites

### System Dependencies

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    debhelper \
    dh-python \
    python3-setuptools \
    python3-wheel \
    python3-stdeb \
    rpm \
    fakeroot
```

#### Fedora/RHEL
```bash
sudo dnf install -y \
    python3 \
    python3-pip \
    python3-gobject \
    python3-cairo \
    gtk4-devel \
    libadwaita-devel \
    rpm-build \
    python3-setuptools \
    python3-wheel
```

### Python Dependencies
```bash
pip3 install -r requirements.txt
pip3 install setuptools wheel stdeb
```

## Building Packages

### DEB Package (Ubuntu/Debian)

```bash
# Build source distribution
python3 setup.py sdist

# Build DEB package
python3 setup.py --command-packages=stdeb.command bdist_deb

# The .deb file will be in deb_dist/
```

### RPM Package (Fedora/RHEL)

```bash
# Create RPM build directories
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Build source distribution
python3 setup.py sdist

# Copy source tarball
cp dist/*.tar.gz ~/rpmbuild/SOURCES/

# Create spec file (see example in .github/workflows/build-packages.yml)
# Copy spec file to ~/rpmbuild/SPECS/

# Build RPM
rpmbuild -ba ~/rpmbuild/SPECS/bluebubbles-client.spec

# The .rpm files will be in ~/rpmbuild/RPMS/ and ~/rpmbuild/SRPMS/
```

### TAR Package (Universal Linux)

```bash
# Build source distribution
python3 setup.py sdist

# Create binary distribution
mkdir -p bluebubbles-client-1.0.0
cp -r src bluebubbles-client-1.0.0/
cp main.py requirements.txt README.md *.desktop *.metainfo.xml bluebubbles-client-1.0.0/
cp -r icons bluebubbles-client-1.0.0/

# Create install/uninstall scripts (see .github/workflows/build-packages.yml for examples)

# Create tarball
tar -czf bluebubbles-client-1.0.0.tar.gz bluebubbles-client-1.0.0
```

### Flatpak Package

#### Prerequisites
```bash
# Install Flatpak and Flatpak Builder
sudo apt install flatpak flatpak-builder  # Ubuntu/Debian
sudo dnf install flatpak flatpak-builder  # Fedora

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install GNOME Platform and SDK
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
```

#### Building
```bash
# Build Flatpak
flatpak-builder build-dir com.github.bluebubbles.client.yml --force-clean

# Create bundle
flatpak build-export export build-dir
flatpak build-bundle export bluebubbles-client.flatpak com.github.bluebubbles.client
```

#### Installing
```bash
# Install the Flatpak
flatpak install --user bluebubbles-client.flatpak

# Run the application
flatpak run com.github.bluebubbles.client
```

## GitHub Actions

The repository includes GitHub Actions workflows that automatically build all package formats:

- **build-packages.yml**: Builds DEB, RPM, and TAR packages
- **flatpak.yml**: Builds Flatpak packages

### Nightly Builds

Nightly builds are automatically triggered daily at 2 AM UTC and create pre-release versions with all package formats.

### Manual Builds

You can trigger builds manually by:
1. Going to the Actions tab in GitHub
2. Selecting the workflow you want to run
3. Clicking "Run workflow"

## Package Installation

### DEB Package
```bash
sudo dpkg -i bluebubbles-client_*.deb
sudo apt-get install -f  # Fix any dependency issues
```

### RPM Package
```bash
sudo rpm -i bluebubbles-client-*.rpm
# or
sudo dnf install bluebubbles-client-*.rpm
```

### TAR Package
```bash
tar -xzf bluebubbles-client-*.tar.gz
cd bluebubbles-client-*
sudo ./install.sh
```

### Flatpak Package
```bash
flatpak install --user bluebubbles-client.flatpak
```

## Testing

After building and installing any package, you can test the application by:

1. Running from command line: `bluebubbles`
2. Looking for "BlueBubbles" in your applications menu
3. Running the desktop file directly

## Troubleshooting

### Common Issues

1. **Missing GTK4/Libadwaita**: Make sure you have the latest GTK4 and Libadwaita packages installed
2. **Python dependencies**: Ensure all requirements from `requirements.txt` are installed
3. **Permissions**: Some package operations may require sudo/root privileges

### Logs

Check application logs at:
- System journal: `journalctl -f --user-unit=bluebubbles`
- Application output: Run `bluebubbles` from terminal to see output

### Getting Help

If you encounter issues:
1. Check the GitHub Issues page
2. Review the application logs
3. Ensure all dependencies are properly installed
4. Try running the application directly with `python3 main.py` to see detailed error messages
