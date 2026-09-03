from openpyxl import load_workbook
from PyQt5.QtWidgets import QFileDialog
from qgis.PyQt import QtWidgets

class ExcelReader:

    def __init__(self, dialog=None):
        self.data = []
        self.dialog = dialog

    def open_file(self):

        filename, _ = QFileDialog.getOpenFileName(
            self.dialog,
            "Выберите файл инклинометрии",
            "",
            "Excel (*.xlsx *.xls)"
        )
        
        if not filename:
            return None

        return filename


    def read_inclinometry(self, filename):
        """
        Чтение таблицы инклинометрии.

        A0 -> Глубина по стволу, м
        B0 -> Зенитный угол, град
        C0 -> Азимут, град
        """

        workbook = load_workbook(
            filename,
            data_only=True
        )

        sheet = workbook.active        

        row = 2        # Номер строки, с которой начинаются данные

        while True:

            md = sheet[f"A{row}"].value

            # дошли до конца таблицы
            if md is None:
                break

            zenith = sheet[f"B{row}"].value
            azimuth = sheet[f"C{row}"].value

            self.data.append({
                "md": float(md),
                "zenith": float(zenith),
                "azimuth": float(azimuth)
            })

            row += 1

        workbook.close()


        return self.data
    
    
    # def fill_table(self):
    #     table = self.dialog.tableInclinometry
    #     table.setRowCount(0)
    #     for row_data in self.data:
    #         row = table.rowCount()
    #         table.insertRow(row)
    #         table.setItem(
    #             row,
    #             0,
    #             QtWidgets.QTableWidgetItem(
    #                 f"{row_data['md']:.2f}"
    #             )
    #         )
    #         table.setItem(
    #             row,
    #             1,
    #             QtWidgets.QTableWidgetItem(
    #                 f"{row_data['zenith']:.2f}"
    #             )
    #         )
    #         table.setItem(
    #             row,
    #             2,
    #             QtWidgets.QTableWidgetItem(
    #                 f"{row_data['azimuth']:.2f}"
    #             )
    #         )