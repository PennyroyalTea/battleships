import asyncio
from aioconsole import ainput

def print_field(field):
    print(' '.join(map(lambda i: chr(ord('A') + i), range(10))))
    print('- ' * 10)
    for i, x in enumerate(field):
        print(' '.join(x), end='')
        print(f' | {i}')

def s_to_pair(s): # 'C6' -> (2, 6)
    return ord(s[0]) - ord('A'), int(s[1])

def is_line(xs, ys):
    xs_sorted, ys_sorted = sorted(xs), sorted(ys)
    xs_line = all(map(lambda p: ord(p[1]) == ord(p[0]) + 1, zip(xs_sorted, xs_sorted[1:])))
    ys_line = all(map(lambda p: p[1] == p[0] + 1, zip(ys_sorted, ys_sorted[1:])))
    xs_same = xs_sorted[0] == xs_sorted[-1]
    ys_same = ys_sorted[0] == ys_sorted[-1]
    return (xs_line and ys_same) or (ys_line and xs_same)

def is_valid(field, ship, n):
    if len(ship) != n:
        return False
    xs, ys = zip(*map(lambda s: (s[0], int(s[1])), ship))
    if not is_line(xs, ys):
        return False
    coords = map(s_to_pair, ship)
    if not all(map(lambda p: field[p[1]][p[0]] == '.', coords)):
        return False
    return True


def update(field, ship, n):
    deltas = [(-1, 0), (0, -1), (1, 0), (0, 1)]
    coords = list(map(s_to_pair, ship))
    for (c0, c1) in coords:
        for (d0, d1) in deltas:
            nx, ny = c0 + d0, c1 + d1
            if nx < 0 or ny < 0 or nx >= 10 or ny >= 10:
                continue
            field[ny][nx] = 'x'
    for (c0, c1) in coords:
        field[c1][c0] = chr(ord('0') + n)


def read():
    field = [['.'] * 10 for _ in range(10)]

    ships_n = [5, 4, 3, 3, 2]
    ships_names = ['авианосец', 'линкор', 'эсминец', 'подлодка', 'сторожевой катер']
    for n, name in zip(ships_n, ships_names):
        while True:
            print_field(field)
            _inp = input(
                f'Выберите {n} клеток в ряд, на которых будет {name}. '
            ).split(' ')
            if is_valid(field, _inp, n):
                update(field, _inp, n)
                break
            else:
                print(f'Некорректный ввод. Попробуйте еще раз')
    print_field(field)
    return field