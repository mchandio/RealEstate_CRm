#!/usr/bin/env bash
# ============================================================================
# Real Estate CRM - Ubuntu Application Builder
# ============================================================================
# Builds a complete .deb package for Ubuntu/Debian Linux systems.
#
# Usage:
#   ./build_ubuntu.sh              # Full build (default)
#   ./build_ubuntu.sh clean        # Clean build artifacts
#   ./build_ubuntu.sh install      # Build + install the .deb package locally
#   ./build_ubuntu.sh deploy       # Deploy to the local system directly
# ============================================================================

set -euo pipefail

APP_NAME="realestate-crm"
APP_VERSION="3.0.0"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGING_DIR="$PROJECT_DIR/packaging"
BUILD_DIR="$PROJECT_DIR/build"
DEB_DIR="$BUILD_DIR/${APP_NAME}_${APP_VERSION}_all"

# Colors
BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "  Real Estate CRM - Ubuntu Application Builder v${APP_VERSION}"
echo "============================================================"
echo -e "${NC}"

# ── Parse arguments ──
ACTION="${1:-build}"

# ── Check for required tools ──
check_tools() {
    local missing=false
    for tool in python3 pip3 find rsync; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            echo -e "${RED}✗ Missing: $tool${NC}"
            missing=true
        fi
    done
    if command -v dpkg-deb >/dev/null 2>&1; then
        echo -e "${GREEN}✓ dpkg-deb available${NC}"
    else
        echo -e "${YELLOW}⚠ dpkg-deb not found (install dpkg-dev for .deb building)${NC}"
    fi
    if command -v fakeroot >/dev/null 2>&1; then
        echo -e "${GREEN}✓ fakeroot available${NC}"
    else
        echo -e "${YELLOW}⚠ fakeroot not found (install for .deb building)${NC}"
    fi
    if $missing; then
        echo -e "${RED}Please install missing tools and try again.${NC}"
        exit 1
    fi
}

# ── Create SVG icon ──
create_icon() {
    local icon_dir="$1"
    mkdir -p "$icon_dir"
    
    cat > "$icon_dir/realestate-crm.svg" << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#167064"/>
      <stop offset="100%" style="stop-color:#0f5d53"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#b7791f"/>
      <stop offset="100%" style="stop-color:#9a6a13"/>
    </linearGradient>
  </defs>
  <rect width="256" height="256" rx="48" fill="url(#bg)"/>
  <!-- Building icon -->
  <rect x="48" y="96" width="48" height="112" rx="4" fill="rgba(255,255,255,0.9)"/>
  <rect x="112" y="56" width="48" height="152" rx="4" fill="rgba(255,255,255,0.85)"/>
  <rect x="176" y="80" width="48" height="128" rx="4" fill="rgba(255,255,255,0.9)"/>
  <!-- Windows -->
  <rect x="56" y="108" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="76" y="108" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="56" y="128" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="76" y="128" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="120" y="68" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="140" y="68" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="120" y="88" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="140" y="88" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="184" y="92" width="12" height="12" rx="1" fill="#167064"/>
  <rect x="204" y="92" width="12" height="12" rx="1" fill="#167064"/>
  <!-- Roof -->
  <polygon points="48,96 96,96 72,72" fill="rgba(255,255,255,0.6)"/>
  <polygon points="112,56 160,56 136,38" fill="rgba(255,255,255,0.6)"/>
  <polygon points="176,80 224,80 200,62" fill="rgba(255,255,255,0.6)"/>
  <!-- Star accent -->
  <polygon points="128,192 132,180 144,180 134,172 138,160 128,168 118,160 122,172 112,180 124,180" fill="url(#accent)"/>
  <!-- Dollar sign -->
  <text x="128" y="216" text-anchor="middle" font-family="Arial, sans-serif" font-weight="bold" font-size="28" fill="rgba(255,255,255,0.9)">CRM</text>
</svg>
SVGEOF
    
    # Convert SVG to PNG if ImageMagick is available
    if command -v convert >/dev/null 2>&1; then
        convert "$icon_dir/realestate-crm.svg" "$icon_dir/realestate-crm.png" 2>/dev/null && \
            echo -e "${GREEN}✓ Created PNG icon${NC}" || \
            echo -e "${YELLOW}⚠ ImageMagick not found, using SVG icon only${NC}"
    fi
    echo -e "${GREEN}✓ Created SVG icon${NC}"
}

# ── Build .deb package ──
build_deb() {
    echo -e "${CYAN}Building .deb package...${NC}"
    
    check_tools
    
    # Clean and prepare build directory
    rm -rf "$BUILD_DIR"
    mkdir -p "$DEB_DIR"
    
    # Create directory structure
    mkdir -p "$DEB_DIR/DEBIAN"
    mkdir -p "$DEB_DIR/opt/realestate-crm"
    mkdir -p "$DEB_DIR/usr/share/applications"
    mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$DEB_DIR/usr/share/icons/hicolor/scalable/apps"
    mkdir -p "$DEB_DIR/usr/share/doc/realestate-crm"
    mkdir -p "$DEB_DIR/lib/systemd/system"
    mkdir -p "$DEB_DIR/var/lib/realestate-crm"
    mkdir -p "$DEB_DIR/var/log/realestate-crm"
    
    # Copy control files
    cp "$PACKAGING_DIR/DEBIAN/control" "$DEB_DIR/DEBIAN/"
    cp "$PACKAGING_DIR/DEBIAN/postinst" "$DEB_DIR/DEBIAN/"
    cp "$PACKAGING_DIR/DEBIAN/prerm" "$DEB_DIR/DEBIAN/"
    cp "$PACKAGING_DIR/DEBIAN/conffiles" "$DEB_DIR/DEBIAN/"
    chmod 755 "$DEB_DIR/DEBIAN/postinst"
    chmod 755 "$DEB_DIR/DEBIAN/prerm"
    
    # Copy application files
    echo "Copying application files..."
    rsync -a --no-g --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
          --exclude='.git' --exclude='build' --exclude='node_modules' \
          --exclude='packaging' --exclude='real_estate_crm.db*' \
          --exclude='.gitignore' --exclude='*.spec' --exclude='*.iss' \
          --exclude='*.bat' --exclude='*.ps1' --exclude='audit_logs' \
          --exclude='.comate' --exclude='*.db.backup*' --exclude='*.db-wal' \
          --exclude='*.db-shm' --exclude='*.sublime-workspace' \
          "$PROJECT_DIR/" "$DEB_DIR/opt/realestate-crm/"
    
    # Copy desktop file
    cp "$PACKAGING_DIR/realestate-crm.desktop" "$DEB_DIR/usr/share/applications/"
    
    # Copy icons
    create_icon "$DEB_DIR/usr/share/icons/hicolor/scalable/apps"
    if [ -f "$DEB_DIR/usr/share/icons/hicolor/scalable/apps/realestate-crm.png" ]; then
        cp "$DEB_DIR/usr/share/icons/hicolor/scalable/apps/realestate-crm.png" \
           "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/"
    fi
    cp "$DEB_DIR/usr/share/icons/hicolor/scalable/apps/realestate-crm.svg" \
       "$DEB_DIR/usr/share/icons/hicolor/scalable/apps/"
    cp "$DEB_DIR/usr/share/icons/hicolor/scalable/apps/realestate-crm.svg" \
       "$DEB_DIR/opt/realestate-crm/realestate-crm.svg"
    
    # Copy systemd service
    cp "$PACKAGING_DIR/realestate-crm.service" "$DEB_DIR/lib/systemd/system/"
    
    # Copy documentation
    for doc in README.md QUICKSTART.md LICENSE; do
        if [ -f "$PROJECT_DIR/$doc" ]; then
            cp "$PROJECT_DIR/$doc" "$DEB_DIR/usr/share/doc/realestate-crm/"
        fi
    done
    
    # Remove .venv from deb copy (will be created by postinst)
    rm -rf "$DEB_DIR/opt/realestate-crm/.venv" 2>/dev/null || true
    
    # Create start script for direct use (not via systemd)
    cat > "$DEB_DIR/opt/realestate-crm/start.sh" << 'SCRIPT'
#!/usr/bin/env bash
# Real Estate CRM - Quick Start Script
cd /opt/realestate-crm
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt -q
fi
if [ ! -f "real_estate_crm.db" ]; then
    .venv/bin/python database_setup.py
fi
echo "Starting Real Estate CRM on http://localhost:6090"
exec .venv/bin/python start_app.py --skip-install
SCRIPT
    chmod +x "$DEB_DIR/opt/realestate-crm/start.sh"
    
    # Strip setgid bits (dpkg-deb rejects 2xxx permissions)
    find "$DEB_DIR" -type d -exec chmod g-s {} \;
    
    # Calculate installed size
    local size_kb=$(du -sk "$DEB_DIR/opt/realestate-crm" 2>/dev/null | cut -f1)
    sed -i "s/Installed-Size:.*/Installed-Size: $size_kb/" "$DEB_DIR/DEBIAN/control"
    
    # Build .deb package
    echo -e "${CYAN}Creating .deb package...${NC}"
    if command -v fakeroot >/dev/null 2>&1; then
        fakeroot dpkg-deb --build "$DEB_DIR" "$BUILD_DIR/"
    else
        dpkg-deb --build "$DEB_DIR" "$BUILD_DIR/"
    fi
    
    local deb_file=$(ls "$BUILD_DIR"/*.deb 2>/dev/null | head -1)
    if [ -n "$deb_file" ]; then
        local size=$(du -h "$deb_file" | cut -f1)
        echo -e "${GREEN}✓ Package created: ${BOLD}$deb_file${NC}"
        echo -e "${GREEN}  Size: $size${NC}"
    else
        echo -e "${RED}✗ Package creation failed${NC}"
        exit 1
    fi
}

# ── Install .deb package ──
install_deb() {
    local deb_file=$(ls "$BUILD_DIR"/*.deb 2>/dev/null | head -1)
    if [ -z "$deb_file" ]; then
        echo -e "${YELLOW}No .deb package found. Building first...${NC}"
        build_deb
        deb_file=$(ls "$BUILD_DIR"/*.deb 2>/dev/null | head -1)
    fi
    
    echo -e "${CYAN}Installing $deb_file...${NC}"
    if command -v gdebi >/dev/null 2>&1; then
        sudo gdebi -n "$deb_file"
    else
        sudo dpkg -i "$deb_file" 2>/dev/null || sudo apt-get install -f -y
    fi
    echo -e "${GREEN}✓ Installation complete!${NC}"
    echo ""
    echo "Access the CRM at: http://localhost:6090"
    echo "Login: admin / admin"
}

# ── Direct deployment (no .deb) ──
deploy_direct() {
    echo -e "${CYAN}Deploying directly to /opt/realestate-crm...${NC}"
    
    sudo mkdir -p /opt/realestate-crm
    sudo mkdir -p /var/lib/realestate-crm
    sudo mkdir -p /var/log/realestate-crm
    
    # Copy application files
    sudo rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
          --exclude='.git' --exclude='build' --exclude='packaging' \
          "$PROJECT_DIR/" "/opt/realestate-crm/"
    
    # Copy desktop file
    sudo cp "$PACKAGING_DIR/realestate-crm.desktop" /usr/share/applications/
    
    # Create icon
    sudo mkdir -p /usr/share/icons/hicolor/256x256/apps
    create_icon /tmp/realestate-crm-icons
    sudo cp /tmp/realestate-crm-icons/realestate-crm.svg /usr/share/icons/hicolor/scalable/apps/ 2>/dev/null || true
    
    # Copy systemd service
    sudo cp "$PACKAGING_DIR/realestate-crm.service" /lib/systemd/system/
    sudo systemctl daemon-reload
    
    # Setup virtual environment
    if [ ! -d "/opt/realestate-crm/.venv" ]; then
        sudo python3 -m venv /opt/realestate-crm/.venv
    fi
    sudo /opt/realestate-crm/.venv/bin/pip install -r /opt/realestate-crm/requirements.txt -q
    
    # Initialize database
    if [ ! -f "/opt/realestate-crm/real_estate_crm.db" ]; then
        sudo /opt/realestate-crm/.venv/bin/python /opt/realestate-crm/database_setup.py
    fi
    
    # Set permissions
    sudo chown -R "$USER:$USER" /opt/realestate-crm /var/lib/realestate-crm /var/log/realestate-crm 2>/dev/null || true
    
    echo -e "${GREEN}✓ Deployment complete!${NC}"
    echo ""
    echo "Start the server:"
    echo "  sudo systemctl start realestate-crm"
    echo "  sudo systemctl enable realestate-crm"
    echo ""
    echo "Or run directly:"
    echo "  cd /opt/realestate-crm && ./start.sh"
}

# ── Clean ──
clean() {
    echo -e "${YELLOW}Cleaning build artifacts...${NC}"
    rm -rf "$BUILD_DIR"
    rm -rf /tmp/realestate-crm-icons
    echo -e "${GREEN}✓ Cleaned${NC}"
}

# ── Main ──
case "$ACTION" in
    clean)
        clean
        ;;
    install)
        build_deb
        install_deb
        ;;
    deploy)
        deploy_direct
        ;;
    help|--help|-h)
        echo "Usage: ./build_ubuntu.sh [ACTION]"
        echo ""
        echo "Actions:"
        echo "  build    Build .deb package (default)"
        echo "  install  Build and install .deb package"
        echo "  deploy   Direct deployment (no .deb)"
        echo "  clean    Clean build artifacts"
        echo "  help     Show this help"
        ;;
    *)
        build_deb
        ;;
esac

echo -e "\n${GREEN}${BOLD}Done!${NC}\n"
