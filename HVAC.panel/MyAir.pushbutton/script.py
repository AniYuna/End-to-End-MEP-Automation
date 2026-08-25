# -*- coding: utf-8 -*-
"""MyAir - Summary air balance for rooms (Spaces)."""

import traceback
from Autodesk.Revit.DB import (
    FilteredElementCollector, 
    BuiltInCategory, 
    BuiltInParameter
)
from pyrevit import revit, forms, script

doc = revit.doc
output = script.get_output()

def run():
    # Чтение параметров
    def get_str_param(elem, param_name):
        p = elem.LookupParameter(param_name)
        if p and p.HasValue:
            val = p.AsString()
            return val if val else u"-"
        return u"-"

    def get_num_param(elem, param_name):
        p = elem.LookupParameter(param_name)
        if p and p.HasValue:
            return p.AsDouble() * 101.940647
        return 0.0

    # 1. Загрузка уровней и пространств
    levels = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_Levels)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    sorted_levels = sorted(levels, key=lambda l: l.Elevation)

    all_spaces = (
        FilteredElementCollector(doc)
        .OfCategory(BuiltInCategory.OST_MEPSpaces)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    # 2. Цикл выбора уровней
    while True:
        selected_levels = forms.SelectFromList.show(
            sorted_levels,
            name_attr='Name',
            title='MyAir: Select levels',
            button_name='Select',
            multiselect=True
        )

        # Если пользователь нажал Отмена или закрыл окно — выходим
        if selected_levels is None:
            return

        selected_ids = [l.Id for l in selected_levels]

        table_data = []

        for sp in all_spaces:
            if selected_ids and sp.LevelId not in selected_ids:
                continue

            num_param = sp.get_Parameter(BuiltInParameter.ROOM_NUMBER)
            name_param = sp.get_Parameter(BuiltInParameter.ROOM_NAME)

            sp_num = num_param.AsString() if (num_param and num_param.HasValue) else unicode(sp.Number)
            sp_name = name_param.AsString() if (name_param and name_param.HasValue) else unicode(sp.Name)

            p_sys = get_str_param(sp, u"ADSK_Наименование приточной системы")
            p_flow = get_num_param(sp, u"ADSK_Расчетный приток")
            
            v_sys = get_str_param(sp, u"ADSK_Наименование вытяжной системы")
            v_flow = get_num_param(sp, u"ADSK_Расчетная вытяжка")

            balance = p_flow - v_flow

            if balance > 0.01:
                colored_balance = u'<span style="color: green; font-weight: bold;">{:+.1f}</span>'.format(balance)
            elif balance < -0.01:
                colored_balance = u'<span style="color: red; font-weight: bold;">{:+.1f}</span>'.format(balance)
            else:
                colored_balance = u'0.0'

            str_p_flow = u"{} ({:.1f} m³/h)".format(p_sys, p_flow) if p_flow > 0 else u"-"
            str_v_flow = u"{} ({:.1f} m³/h)".format(v_sys, v_flow) if v_flow > 0 else u"-"

            table_data.append([
                sp_num or u"-",
                sp_name or u"No name",
                str_p_flow,
                str_v_flow,
                colored_balance
            ])

        # Проверка на пустой результат
        if not table_data:
            forms.alert(
                u"The selected level does not contain any Spaces for calculation.",
                title=u"Information",
                warn_icon=True
            )
            continue  # Возврат к выбору уровней

        # Если данные есть — сортируем, выводим таблицу и завершаем цикл
        table_data = sorted(table_data, key=lambda x: str(x[0]))

        output.print_md("### Consolidated air balance for Spaces")

        columns = [u"Number", u"Name", u"Supply air", u"Exhaust air", u"Imbalance (m³/h)"]
        output.print_table(
            table_data=table_data,
            columns=columns,
            title=u"Processed Spaces: {}".format(len(table_data))
        )
        break

try:
    run()
except Exception as e:
    output.print_md("### ❌ Error:")
    print(traceback.format_exc())