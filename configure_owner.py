"""One-time local setup. This function is intentionally absent from web signup."""
from getpass import getpass
import classroom


def main():
    print('Coach Chess — configurar o Superadministrador (criador)')
    name=input('Seu usuário: ').strip()
    password=getpass('Sua senha (pelo menos 8 caracteres): ')
    if password!=getpass('Confirme sua senha: '):
        raise ValueError('As senhas não conferem.')
    token=classroom.bootstrap_owner(name,password)
    classroom.logout(token)
    print('Superadministrador configurado. Abra o aplicativo e entre com seu usuário e senha.')


if __name__=='__main__':
    try:main()
    except (ValueError,EOFError,KeyboardInterrupt) as error:
        print(str(error) or 'Configuração cancelada.')
        raise SystemExit(1)
