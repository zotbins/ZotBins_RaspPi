"""
Dependencies:
sudo apt-get install qt5-default
sudo pip install pyqt5
sudo apt-get install qt5-default pyqt5-dev pyqt5-dev-tools

"""
import sys
from PyQt5.QtWidgets import QApplication, QWidget

def app():
    my_app = QApplication(sys.argv)
    w = QWidget()
    w.setWindowTitle("Testing this stuff")
    w.show()
    sys.exit(my_app.exec_())

if __name__ == "__main__":
    app()

