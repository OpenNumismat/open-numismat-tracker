#!/usr/bin/env python3

import os
import shutil
import PyQt5

pyqtPath = PyQt5.__path__[0]
translationsPath = os.path.join(pyqtPath, "translations")
lupdatePath = os.path.join(pyqtPath, 'pylupdate4.exe')
linguistPath = os.path.join(pyqtPath, 'linguist.exe')
lreleasePath = os.path.join(pyqtPath, 'lrelease.exe')

srcFiles = []
for dirname, dirnames, filenames in os.walk('../OpenNumismat'):
    for filename in filenames:
        fileName, fileExtension = os.path.splitext(filename)
        if fileExtension == '.py':
            srcFiles.append(os.path.join(dirname, filename))

for locale in ['ru', 'uk', 'es', 'hu']:
    outputfile = 'lang_%s.ts' % locale
    os.system(' '.join([lupdatePath, ' '.join(srcFiles), '-ts', outputfile]))
    os.system(' '.join([linguistPath, outputfile]))
    dst_file = '../OpenNumismat/lang_%s.qm' % locale
    os.system(' '.join([lreleasePath, outputfile, '-qm', dst_file]))

    src_file = os.path.join(translationsPath, "qt_%s.qm" % locale)
    shutil.copy(src_file, "../OpenNumismat")
