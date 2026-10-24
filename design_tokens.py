"""Shared Coach Chess colors. All screens use the same dark palette."""
LIGHT = dict(background='#F5F3ED', surface='#FFFEFA', soft='#ECEFE8', ink='#202B26',
             muted='#626F66', border='#D9DED5', accent='#176B4A', accent_soft='#E3EFE6', accent_ink='#FFFFFF', gold='#8A6A35')
DARK = dict(background='#0a0a0a', surface='#191919', soft='#232323', ink='#f5f5f5',
            muted='#a3a3a3', border='#343434', accent='#ff8000', accent_soft='#332011', accent_ink='#ffffff', gold='#c7c7c7')


def palette(dark=False):
    # Keep the argument for compatibility with existing components and saved UI settings.
    return DARK.copy()
