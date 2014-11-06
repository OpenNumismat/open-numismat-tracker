import codecs
import locale
import os
import shutil

try:
# TODO: For speedup use additional a http://pypi.python.org/pypi/MarkupSafe
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print('jinja2 module missed. Report engine not available')
try:
    import numpy
except ImportError:
    print('numpy module missed. Trend functionality not available')

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt

from OpenNumismat.Collection.CollectionFields import FieldTypes as Type
from OpenNumismat.Tools import Gui
import OpenNumismat


def formatFields(field, data):
    try:
        if field.type == Type.BigInt:
            text = locale.format("%d", int(data), grouping=True)
        elif field.type == Type.Money:
            text = locale.format("%.2f", float(data), grouping=True)
            dp = locale.localeconv()['decimal_point']
            text = text.rstrip('0').rstrip(dp)
        elif field.type == Type.Value:
            text = locale.format("%.3f", float(data), grouping=True)
            dp = locale.localeconv()['decimal_point']
            text = text.rstrip('0').rstrip(dp)
        elif field.type == Type.Date:
            date = QtCore.QDate.fromString(data, Qt.ISODate)
            text = date.toString(Qt.SystemLocaleShortDate)
        elif field.type == Type.DateTime:
            date = QtCore.QDateTime.fromString(data, Qt.ISODate)
            # Timestamp in DB stored in UTC
            date.setTimeSpec(Qt.UTC)
            date = date.toLocalTime()
            text = date.toString(Qt.SystemLocaleShortDate)
        else:
            return data
    except (ValueError, TypeError):
        return data
    return text


def copyFolder(sourceFolder, destFolder):
    sourceDir = QtCore.QDir(sourceFolder)
    if not sourceDir.exists():
        return

    destDir = QtCore.QDir(destFolder)
    if not destDir.exists():
        destDir.mkpath(destFolder)

    files = sourceDir.entryList(QtCore.QDir.Files)
    for file in files:
        srcName = os.path.join(sourceFolder, file)
        destName = os.path.join(destFolder, file)
        QtCore.QFile.remove(destName)  # remove if existing
        QtCore.QFile.copy(srcName, destName)

    files = sourceDir.entryList(QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot)
    for file in files:
        srcName = os.path.join(sourceFolder, file)
        destName = os.path.join(destFolder, file)
        copyFolder(srcName, destName)


def scanTemplates():
    templates = []

    sourceDir = QtCore.QDir(os.path.join(OpenNumismat.PRJ_PATH, Report.BASE_FOLDER))
    if not sourceDir.exists():
        return templates

    files = sourceDir.entryList(QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot)
    for file in files:
        templates.append(file)

    return templates


class Report(QtCore.QObject):
    BASE_FOLDER = 'templates'

    def __init__(self, model, template_name, dstPath, parent=None):
        super(Report, self).__init__(parent)

        self.model = model
        self.srcFolder = os.path.join(OpenNumismat.PRJ_PATH, self.BASE_FOLDER, template_name)

        fileInfo = QtCore.QFileInfo(dstPath)
        if fileInfo.exists() and fileInfo.isDir():
            self.dstFolder = dstPath
            self.fileName = None
        else:
            self.dstFolder = fileInfo.dir().path()
            self.fileName = fileInfo.fileName()

    def generate(self, records, single_file=False):
        if os.path.exists(os.path.join(self.srcFolder, 'coin.htm')):
            has_item_template = True
        else:
            has_item_template = False
            single_file = True

        self.mapping = {'single_file': single_file,
                        'date': QtCore.QDate.currentDate().toString(QtCore.Qt.DefaultLocaleLongDate)}

        self.mapping['collection'] = {'title': self.model.description.title,
                            'description': self.model.description.description,
                            'author': self.model.description.author}

        if not self.fileName:
            if len(records) == 1 and has_item_template:
                self.fileName = "coin_%d.htm" % records[0].value('id')
            else:
                self.fileName = "coins.htm"
        static_files = QtCore.QFileInfo(self.fileName).baseName() + '_files'
        self.contentDir = os.path.join(self.dstFolder, static_files)

        self.mapping['static_files'] = static_files

        copyFolder(os.path.join(self.srcFolder, 'files'), self.contentDir)

        loader = FileSystemLoader(self.srcFolder)
        self.env = Environment(loader=loader, autoescape=True)

        titles_mapping = {}
        for field in self.model.fields:
            titles_mapping[field.name] = field.title
        self.mapping['titles'] = titles_mapping

        if len(records) == 1 and has_item_template:
            self.mapping['record'] = self.__recordMapping(records[0])
            dstFile = self.__render('coin.htm', self.fileName)
        else:
            progressDlg = Gui.ProgressDialog(self.tr("Generating report"),
                            self.tr("Cancel"), len(records), self.parent())

            record_data = []
            points = []
            if records:
                start_date = QtCore.QDate.fromString(records[0].value('date'), Qt.ISODate)

            for record in records:
                progressDlg.step()
                if progressDlg.wasCanceled():
                    return None

                recordMapping = self.__recordMapping(record)
                record_data.append(recordMapping)
                if not single_file:
                    self.mapping['record'] = recordMapping
                    self.__render('coin.htm', "coin_%d.htm" % record.value('id'))

                days = QtCore.QDate.fromString(record.value('date'), Qt.ISODate).daysTo(start_date)
                points.append((days, record.value('price')))

            trend = []
            if records:
                progressDlg.setLabelText(self.tr("Generating trend"))

                points.sort(key=lambda tup: tup[0], reverse=True)
                coefficients = numpy.polyfit([tup[0] for tup in points], [tup[1] for tup in points], 3)
                polynomial = numpy.poly1d(coefficients)
                min_x = points[0][0]  # min(x)
                max_x = points[-1][0]
                if min_x - max_x > 100:
                    delimeter = 100
                else:
                    delimeter = min_x - max_x
                xs = numpy.arange(min_x, max_x - 1, (max_x - min_x) / delimeter)
                ys = polynomial(xs)

                for i in range(len(xs)):
                    date = start_date.addDays(-xs[i])
                    point = {'date_js': '%d,%d,%d' % (date.year(), date.month() - 1, date.day()),
                         'date': date.toString(Qt.SystemLocaleShortDate),
                         'price_raw': numpy.round(ys[i]).astype(int)}
                    trend.append(point)

            self.mapping['records'] = record_data
            self.mapping['trend'] = trend

            progressDlg.setLabelText(self.tr("Write report"))
            dstFile = self.__render('coins.htm', self.fileName)

            progressDlg.reset()

        return dstFile

    def __render(self, template, fileName):
        template = self.env.get_template(template)
        res = template.render(self.mapping)

        dstFile = os.path.join(self.dstFolder, fileName)
        f = codecs.open(dstFile, 'w', 'utf-8')
        f.write(res)
        f.close()

        return dstFile

    def __recordMapping(self, record):
        imgFields = ['photo1', 'photo2', 'photo3', 'photo4']

        record_mapping = {}
        record_mapping['date_js'] = ''
        record_mapping['date_raw'] = ''
        record_mapping['price_raw'] = ''
        for field in self.model.fields:
            value = record.value(field.name)
            if value is None or value == '':
                record_mapping[field.name] = ''
            else:
                if field.name in imgFields:
                    if field.name == 'image':
                        ext = 'png'
                    else:
                        ext = 'jpg'

                    imgFileTitle = "%s_%d.%s" % (field.name, record.value('id'), ext)
                    imgFile = os.path.join(self.contentDir, imgFileTitle)

                    photo = record.value(field.name)
                    srcFile = photo.fileName()
                    if srcFile:
                        shutil.copyfile(srcFile, imgFile)
                        record_mapping[field.name] = imgFileTitle
                    else:
                        record_mapping[field.name] = ''
                else:
                    record_mapping[field.name] = formatFields(field, value)
                    if field.name == 'date':
                        parts = value.split('-')
                        record_mapping['date_js'] = '%d,%d,%d' % (int(parts[0]), int(parts[1]) - 1, int(parts[2]))
                        record_mapping['date_raw'] = value
                    if field.name == 'price':
                        record_mapping['price_raw'] = value

        return record_mapping
