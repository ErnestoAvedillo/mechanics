from . import demo


def demo_user(request):
    """Lets templates hide what a demo user must not use (e.g. the account page)."""
    return {'is_demo_user': demo.is_demo(request.user)}
