# -*- coding: utf-8 -*-

from datagrid.grids import DataGrid, Column, NonDatabaseColumn

class ShiftGrid(DataGrid):
    when = Column()
    span = Column()
    exam_period = Column()
    enabled = Column()
