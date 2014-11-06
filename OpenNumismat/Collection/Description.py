from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlQuery
from PyQt5.QtWidgets import *


class CollectionDescription(QtCore.QObject):
    def __init__(self, collection):
        super(CollectionDescription, self).__init__(collection)
        self.db = collection.db

        if 'description' not in self.db.tables():
            self.create(collection)

        query = QSqlQuery("SELECT * FROM description", self.db)
        query.first()
        record = query.record()

        self.title = record.value('title')
        self.description = record.value('description')
        self.author = record.value('author')

    def save(self):
        self.db.transaction()

        query = QSqlQuery(self.db)
        query.prepare("UPDATE description SET title=?, description=?,"
                      " author=? WHERE id=1")
        query.addBindValue(self.title)
        query.addBindValue(self.description)
        query.addBindValue(self.author)
        query.exec_()

        self.db.commit()

    def create(self, collection):
        self.db.transaction()

        sql = """CREATE TABLE description (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            author TEXT)"""
        QSqlQuery(sql, self.db)

        query = QSqlQuery(self.db)
        query.prepare("""INSERT INTO description (title, description, author)
                VALUES (?, ?, ?)""")
        query.addBindValue(collection.getCollectionName())
        query.addBindValue('')
        query.addBindValue('')
        query.exec_()

        self.db.commit()


class DescriptionDialog(QDialog):
    def __init__(self, description, parent=None):
        super().__init__(parent,
                         Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)

        self.description = description

        self.setWindowTitle(self.tr("Description"))

        mainLayout = QFormLayout()

        self.titleWidget = QLineEdit(self.description.title, self)
        mainLayout.addRow(self.tr("Title"), self.titleWidget)
        self.descriptionWidget = QTextEdit(self)
        self.descriptionWidget.setText(self.description.description)
        self.descriptionWidget.setAcceptRichText(False)
        self.descriptionWidget.setTabChangesFocus(True)
        mainLayout.addRow(self.tr("Description"), self.descriptionWidget)
        self.authorWidget = QLineEdit(self.description.author, self)
        mainLayout.addRow(self.tr("Author"), self.authorWidget)

        buttonBox = QDialogButtonBox(Qt.Horizontal)
        buttonBox.addButton(QDialogButtonBox.Ok)
        buttonBox.addButton(QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.save)
        buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(mainLayout)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

    def save(self):
        self.description.title = self.titleWidget.text()
        self.description.description = self.descriptionWidget.toPlainText()
        self.description.author = self.authorWidget.text()
        self.description.save()

        self.accept()
