import asyncio
from aioconsole import ainput

def print_field(field):
    print(' '.join(map(lambda i: chr(ord('A') + i), range(10))))
    print('- ' * 10)
    for i, x in enumerate(field):
        print(' '.join(x), end='')
        print(f' | {i}')

def is_valid(field, ship, n):
    if len(ship) != n:
        return False
    xs, ys = zip(*map(lambda s: (s[0], int(s[1])), ship))
    print(f'xs: {xs}, ys: {ys}')

def update(field, ship):
    pass

async def read():
    field = [['.'] * 10 for _ in range(10)]
    ships_n = [5, 4, 3, 3, 2]
    ships_names = ['авианосец', 'линкор', 'эсминец', 'подлодка', 'сторожевой катер']
    for n, name in zip(ships_n, ships_names):
        while True:
            print_field(field)
            _inp = input(f'Выберите {n} клеток в ряд, на которых будет {name}').split(' ')
            if is_valid(field, _inp, n):
                update(field, _inp)
                break
            else:
                print(f'Некорректный ввод. Попробуйте еще раз')

    return field