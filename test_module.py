from bytepatches.decorators import omit_return, replace, optimize

if __name__ == "__main__":
    @replace("p=1", "p=3")
    @replace("p-3", "p-4")
    def f():
        p = 1
        print = lambda x: None
        print(p)
        return p - 3


    assert f() == -1


    @omit_return
    def add(a, b):
        a + b


    assert add(1, 2) == 3


    @omit_return
    def choose(cond, if_true, if_false):
        if cond:
            if_true
        elif cond is None:
            # Putting `None` or any other const directly will not register
            # due to compiler optimizations that we cant fix,
            # so for now we just assign to `x` first as
            # [LOAD_NAME POP_TOP] is not filtered out
            x = None
            x
        else:
            if_false


    assert choose(True, 1, 2) == 1
    assert choose(False, 1, 2) == 2
    assert choose(None, 1, 2) is None


    @omit_return
    def loop_return(x):
        for i in range(10):
            if i > 3:
                i + x
            else:
                x - i


    assert loop_return(5) == 14


    # The next function should get optimized
    @optimize
    def unoptimized_func():
        x = 1
        y = x
        z = y
        return z


    def optimized_func():
        return 1


    assert optimized_func.__code__.co_code == unoptimized_func.__code__.co_code


    # Test by juanita
    @optimize
    def juanita_test():
        for i in range(10):
            j = i

        return j


    def juanita_optimized():
        for j in range(10):
            pass

        return j


    assert juanita_test.__code__.co_code == juanita_optimized.__code__.co_code
