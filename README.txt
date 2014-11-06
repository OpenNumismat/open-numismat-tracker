Requirement:
 * Python 3.3.1
 * PyQt5 4.10
 * Jinja2 2.6 (for reports)
 * lxml 3.1.2 (for auction parsing) [http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml]
 * cssselect 0.8

 * xlwt3 0.1.2 (for exporting to Excel)
 * pywin32-218 (for saving report as Word Document)
 * cx_Freeze 4.3.1 (for deploy)
 * distribute/setuptools 0.6 (for deploy)
 * Inno Setup 5.5.3 (for deploy)

Deploying:
Run `python i18n.py` and fill translations
Run `python setup.py build`
Compile setup*.iss with Inno Setup
