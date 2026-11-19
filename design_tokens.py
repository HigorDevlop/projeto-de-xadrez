"""Shared Coach Chess colors. All screens use the same dark palette."""
LIGHT = dict(background='#F5F3ED', surface='#FFFEFA', soft='#ECEFE8', ink='#202B26',
             muted='#626F66', border='#D9DED5', accent='#176B4A', accent_soft='#E3EFE6', accent_ink='#FFFFFF', gold='#8A6A35')
DARK = dict(background='#020d20', surface='#062038', soft='#0a334a', ink='#d9f5ff',
            muted='#90b2c8', border='#17617b', accent='#16cfe4', accent_soft='#08465c', accent_ink='#001421', gold='#ff9b4e')


def palette(dark=False):
    # Keep the argument for compatibility with existing components and saved UI settings.
    return DARK.copy()
