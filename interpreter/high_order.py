from typing import TypeVar, Callable, List, Any


A = TypeVar('A')
B = TypeVar('B')
C = TypeVar('C')


# foldL:: (A -> B -> B) -> B -> [A] -> B
def foldL(function: Callable[[B, A], B], basis: B, lijst: List[A]) -> B:
    if len(lijst) == 0:
        return basis
    else:
        head, *tail = lijst
    return function(foldL(function, basis, tail), head)


# foldL1:: (A -> A -> A) -> [A] -> A
def foldL1(function: Callable[[A, A], A], lijst: List[A]) -> A:
    if len(lijst) == 0:
        raise TypeError("foldL1() with empty sequence is not possible")
    else:
        return foldL(function, lijst[-1], lijst[:-1])


# foldR:: (A -> B -> B) -> B -> [A] -> B
def foldR(function: Callable[[A, B], B], basis: B, lijst: List[A]) -> B:
    return foldL(lambda x, y: function(y, x), basis, lijst)


# foldR1:: (A -> A -> A) -> [A] -> A
def foldR1(function: Callable[[A, A], A], lijst: List[A]) -> A:
    if len(lijst) == 0:
        raise TypeError("foldR1() with empty sequence is not possible")
    return foldL(lambda x, y: function(y, x), lijst[-1], lijst[:-1])


# zipWith:: (A -> B -> C) -> [A] -> [B] -> [C]
def zipWith(f: Callable[[A, B], C], xs: List[A], ys: List[B]) -> List[C]:
    return [f(a, b) for (a, b) in zip(xs, ys)]


if __name__ == '__main__':
    print(foldL1(lambda a, b: a+b, ["1", "2", "3"]))    # 10-5-4 = 1
    print(foldR1(lambda a, b: a+b, ["1", "2", "3"]))  # 10-(5-4) = 9

    print(zipWith(lambda a, b: a*b, [1, 2, 3], [4, 5, 6]))

    print(list(zip([1, 2, 3], [4, 5, 6])))

    print(list(map(lambda x: str(x), [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])))
