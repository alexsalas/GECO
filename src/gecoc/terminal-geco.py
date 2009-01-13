#!/usr/bin/python
# -*- coding: utf-8 -*-
# TODO cifrar/descifrar passwords

'''
Terminal GECO client
'''

import gecolib
import sys
import os
import types
import datetime
import getpass
import threading

TIMEOUT = 10.0 * 60 # 10 minutos
debug = True

def login(server='https://localhost:4343'):
    ''' Autentica contra un servidor 
        login https://localhost:4343
    '''
    global gso
    unix_user = os.environ.get('USER', '')
    user = raw_input('usuario [' + unix_user + ']: ')
    if not user:
        user = unix_user
    password = getpass.getpass()
    gso = gecolib.GSO(xmlrpc_server=server)
    gso.auth(user, password)

def change_password():
    ''' Cambia la contraseña del usuario en el servidor '''
    
    global gso

    password = getpass.getpass('Introduce la nueva contraseña: ')
    password2 = getpass.getpass('Introducela de nuevo: ')

    while password != password2:
        print "No coinciden, intentalo de nuevo"
        password = getpass.getpass('Introduce la nueva contraseña: ')
        password2 = getpass.getpass('Introducela de nuevo: ')
    
    gso.change_password(password)

def logout():
    ''' Cierra la sesión con el servidor '''
    global gso
    gso.logout()

def list():
    ''' Lista todas las contraseñas '''

    global gso
    passwords = gso.get_all_passwords()
                
    formatted = '%-10s | %-20s | %-10s | %-24s'
    header = formatted % ('NAME', 'ACCOUNT',
                'TYPE', 'EXPIRATION')
    print header
    print '='*len(header)
    for p in passwords:
        name = p.get('name', 'NONAME')
        account = p.get('account', '--')
        type = p.get('type', '--')
        expiration = p.get('expiration')
        expiration = datetime.datetime.fromtimestamp(expiration).ctime()
        
        print formatted % (name, account,
                type, expiration)

def get(name=''):
    ''' Devuelve una contraseña en concreto
        get [nombre] 
    '''

    global gso
    if not name:
        name = raw_input('nombre del password: ')

    master_password = _get_master()
    password = gso.get_password(name, master_password)
    print password['password']

def getcp(name=''):
    ''' Devuelve una contraseña en concreto en el portapapeles (solo funciona con GTK)
        getcp [nombre] 
    '''

    global gso
    if not name:
        name = raw_input('nombre del password: ')

    master_password = _get_master()
    password = gso.get_password(name, master_password)
    import pygtk
    pygtk.require('2.0')
    import gtk

    # get the clipboard
    clipboard = gtk.clipboard_get()
    clipboard.set_text(password['password'])
    clipboard.store()

def new(name=''):
    ''' Almacena un password en el servidor 
        new [nombre] 
    '''
    # TODO dejar poner el tiempo de expiracion

    while not name:
        name = raw_input('Nombre para esta contraseña: ')
    args = dict(type='generic',
            description='',
            account='')
    _ask(args)

    print ""
    print "Selecciona el modo de introducción de contraseña:"
    print "[1] Aleatoria de 11 caracteres con mayusculas minusculas y números"
    print " 2  Generación aleatoria personalizada"
    print " 3  Introducción manual"
    mode = raw_input("modo?: ")
        
    if mode in ['', '1']:
        password = gecolib.generate()
    elif mode == '2':
        size = _input('Número de caracteres [11]: ', 11, int)
        lower = _input('Utilizar minusculas? [Y/n]: ', True, bool)
        upper = _input('Utilizar mayusculas? [Y/n]: ', True, bool)
        digits = _input('Utilizar digitos? [Y/n]: ', True, bool)
        punctuation = _input('Utilizar signos de puntuación? [y/N]: ', False, bool)
        
        while True:
            password = gecolib.generate(size, lower, upper, digits,
                    punctuation)
            print password, 'seguridad: ', gecolib.strength(password)
            if _input('Usar este password? [Y/n]: ', True, bool):
                break;
    elif mode == '3':
        password = getpass.getpass('Introduce la contraseña: ')
        password2 = getpass.getpass('Introduce la contraseña de nuevo: ')

        while password != password2:
            print "No coinciden, intentalo de nuevo"
            password = getpass.getpass('Introduce la contraseña: ')
            password2 = getpass.getpass('Introduce la contraseña de nuevo: ')


    master = _get_master()
    gso.set_password(name, password, master, args)

def register(server, name=''):
    ''' Registra un usuario nuevo en el servidor 
        register server [usuario]
    '''
    global gso 
    gso = gecolib.GecoClient(server=server)

    if not gso.check_user_name(name):
        print "Este nombre no está disponible"
        name = ''
    while not name:
        name = raw_input('Nombre de usuario: ')
        if not gso.check_user_name(name):
            print "Este nombre no está disponible"
            name = ''
    password = getpass.getpass('Contraseña de usuario '
                               '(Esta tienes que recordarla): ')
    password2 = getpass.getpass('Repitela: ')
    while password != password2:
        print "No coinciden las contraseñas, intentalo otra vez"
        password = getpass.getpass('Contraseña de usuario '
                                   '(Esta tienes que recordarla): ')
        password2 = getpass.getpass('Repitela: ')
    gso.register(name, password)

def unregister():
    ''' Elimina una cuenta de usuario del servidor '''
    gso.unregister()

def rm(name=''):
    ''' Borra una contraseña del servidor
        rm [nombre] 
    '''

    global gso
    if not name:
        name = raw_input('nombre del password: ')

    gso.del_password(name)

def help(*args):
    ''' Muestra esta ayuda '''
    if args:
        try:
            print callable_functions[args[0]].__doc__
        except:
            print "No encuentro el comando"
    else:
        print help_str

def quit():
    ''' Salir '''
    pass

def forget():
    ''' Olvida la contraseña maestra '''
    global THREAD
    if THREAD:
        THREAD.cancel()
    _forget()

def _ask(args):
    for arg, value in args.items():
        new_value = raw_input(arg + ' [' + value + ']: ')
        if not new_value:
            new_value = value
        args[arg] = new_value

def _forget():
    global master
    del master
    master = ''
    print "Se me olvidó la contraseña maestra"

def _input(prompt, default='', parser=str):
    message = raw_input(prompt)
    if not message:
        return default
    else:
        if parser == bool:
            if message in 'NOno':
                message = ''
        return parser(message)

def _get_master():
    global master
    global THREAD
    if not master:
        master_password = getpass.getpass('Contraseña maestra: ')
        answer = _input('recordar contraseña? (10 min) [Y/n]', True,
                bool)
        if answer:
            master = master_password
            THREAD = threading.Timer(TIMEOUT, _forget)
            THREAD.start()

    else:
        master_password = master
    return master_password

# Muestra todas las funciones como opciones
help_str = ''' Ayuda de terminal-geco
comandos:
''' 

functions = [v for v in globals().values()\
        if type(v) == types.FunctionType\
        if not v.__name__.startswith('_')]
function_names = [v.__name__ for v in functions]
callable_functions = dict(zip(function_names, functions))

# Componiendo la ayuda de las funciones a partir de la documentación
for function in functions:
    help_str += '    "%(opt)s" %(desc)s\n' %\
            {'opt': function.__name__,
             'desc': function.__doc__}


if __name__ == '__main__':
    quit = False
    gso = gecolib.GecoClient(server=None)
    master = ''
    args = ''
    THREAD = None
    history = []
    while not quit:
        history.append(args)
        prompt = 'geco [%s]> ' % gso.name
        try:
            args = raw_input(prompt)
        except:
            quit = True
            print "bye"
            continue
        args = args.split(' ')
        if args[0] == 'quit':
            quit = True

        elif not args[0] in function_names:
            help()
        else:
            try:
                callable_functions[args[0]](*args[1:])
            except Exception, inst:
                if debug:
                    raise inst
                print "Error al ejecutar '%s'" % ' '.join(args)

    forget()
