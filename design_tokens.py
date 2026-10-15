"""Paletas compartilhadas pela interface editorial do Acervo."""
LIGHT = dict(background='#F5F3ED', surface='#FFFEFA', soft='#ECEFE8', ink='#202B26',
             muted='#626F66', border='#D9DED5', accent='#176B4A', accent_soft='#E3EFE6', accent_ink='#FFFFFF', gold='#8A6A35')
DARK = dict(background='#111A16', surface='#1A2720', soft='#223329', ink='#EDF3ED',
            muted='#ACBCAF', border='#354A3C', accent='#85C69A', accent_soft='#263E30', accent_ink='#12251A', gold='#CFB780')


def palette(dark=False):
    return (DARK if dark else LIGHT).copy()
