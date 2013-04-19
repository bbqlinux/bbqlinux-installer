# Maintainer: Daniel Hillenbrand <codeworkx@bbqlinux.org>

pkgname=bbqlinux-installer
pkgver=0.2.0
pkgrel=1
pkgdesc="The BBQLinux Installer"
arch=('any')
url="https://github.com/bbqlinux/bbqlinux-installer"
license=('GPL')
depends=('inxi' 'python2' 'qt4' 'python2-pyqt' 'parted>=3.0' 'pyparted>=3.8' 'python2-geoip')
replaces=('bbqinstaller')

package() {
  cd "$pkgdir"

  install -Dm755 "$srcdir/usr/bin/bbqlinux-installer" usr/bin/bbqlinux-installer

  cp -R "$srcdir/etc" etc
  cp -R "$srcdir/usr/lib" usr/lib
  cp -R "$srcdir/usr/share" usr/share
}
