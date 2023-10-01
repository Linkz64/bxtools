"""
LICENSE INFO: Licenses are per source
"""


"""Fast64
SOURCE: https://github.com/Fast-64/fast64
LICENSE INFO: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007 (https://github.com/Fast-64/fast64/blob/main/LICENSE.txt)
"""
def prop_split(layout, data, field, name, spacing=0.5, **prop_kwargs):
    split = layout.split(factor=spacing)
    split.label(text=name)
    split.prop(data, field, text="", **prop_kwargs)