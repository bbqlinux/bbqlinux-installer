# Maintainer: Daniel Hillenbrand <codeworkx@bbqlinux.org

pkgname=bbqlinux-installer
pkgver=0.0.2
pkgrel=1
pkgdesc="The BBQLinux Installer"
arch=('any')
url="https://github.com/bbqlinux/bbqlinux-installer"
license=('GPL')
depends=('inxi' 'python2' 'qt' 'pyqt' 'parted>=3.0' 'pyparted>=3.8' 'python-geoip')
replaces=('bbqinstaller')

package() {
  cd "$pkgdir"

  install -Dm644 "$srcdir/etc/bbqlinux-installer/install.conf" etc/bbqlinux-installer/install.conf

  install -Dm755 "$srcdir/usr/bin/bbqlinux-installer" usr/bin/bbqlinux-installer

  install -Dm655 "$srcdir/usr/lib/bbqlinux-installer/configobj.py" usr/lib/bbqlinux-installer/configobj.py
  install -Dm655 "$srcdir/usr/lib/bbqlinux-installer/installer.py" usr/lib/bbqlinux-installer/installer.py
  install -Dm755 "$srcdir/usr/lib/bbqlinux-installer/main.py" usr/lib/bbqlinux-installer/main.py
  install -Dm655 "$srcdir/usr/lib/bbqlinux-installer/ui/__init__.py" usr/lib/bbqlinux-installer/ui/__init__.py
  install -Dm655 "$srcdir/usr/lib/bbqlinux-installer/ui/qt_interface.py" usr/lib/bbqlinux-installer/ui/qt_interface.py

  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/countries" usr/share/bbqlinux-installer/countries
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/languages" usr/share/bbqlinux-installer/languages
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/locales" usr/share/bbqlinux-installer/locales
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/logo.svg" usr/share/bbqlinux-installer/logo.svg
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/qt_interface.ui" usr/share/bbqlinux-installer/qt_interface.ui
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/qt_partition_edit_dialog.ui" usr/share/bbqlinux-installer/qt_partition_edit_dialog.ui
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/qt_resources.qrc" usr/share/bbqlinux-installer/qt_resources.qrc
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/qt_resources_rc.py" usr/share/bbqlinux-installer/qt_resources_rc.py
  install -Dm655 "$srcdir/usr/share/bbqlinux-installer/timezones" usr/share/bbqlinux-installer/timezones

  cp -R "$srcdir/usr/share/bbqlinux-installer/flags" usr/share/bbqlinux-installer/flags
  cp -R "$srcdir/usr/share/bbqlinux-installer/icons" usr/share/bbqlinux-installer/icons
}
