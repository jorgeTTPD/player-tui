# Maintainer: Jorge <jorgeescalera500@gmail.com>
pkgname=player-tui
pkgver=1.2.0
pkgrel=1
pkgdesc="Terminal music player with synchronized lyrics"
arch=('any')
url="https://github.com/jorgeTTPD/player-tui"
license=('MIT')
depends=('python' 'python-textual>=0.80' 'python-dbus' 'python-websockets')
makedepends=('python-build' 'python-installer' 'python-wheel')
source=("${pkgname}-${pkgver}.tar.gz")
sha256sums=('SKIP')

build() {
  cd "${srcdir}/player-tui-${pkgver}"
  python -m build --wheel --no-isolation
}

package() {
  cd "${srcdir}/player-tui-${pkgver}"
  python -m installer --destdir="${pkgdir}" dist/*.whl
}
