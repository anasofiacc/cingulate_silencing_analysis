
def check_assertion_error(statement, printed_output):

    try:
        assert statement

    except AssertionError:

        print(printed_output)
