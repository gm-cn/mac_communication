
# -*- coding: utf-8 -*- 
import  xdrlib ,sys
import  xlrd
 
 
def open_excel(file= 'base.xlsx'):
    try:
        data = xlrd.open_workbook(file)
        return data
    except Exception,e:
        print str(e)
 
 
def excel_table_byname(file= 'base.xlsx', colnameindex=0, by_name=u'Sheet1'):
    data = open_excel(file) 
    table = data.sheet_by_name(by_name) 
    nrows = table.nrows
    colnames = table.row_values(colnameindex)
    list =[]
    for rownum in range(0, nrows): 
         row = table.row_values(rownum)
         if row: 
             app = [] 
             for i in range(len(colnames)):
                app.append(row[i])
             list.append(app) 
    return list
 
 
def main():
   tables = excel_table_byname()
   for row in tables:
       print row
 
 
if __name__=="__main__":
    main()
