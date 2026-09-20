"""Canonical actor collapse for documented Wladimir / laanwj variants."""

from src.utils.maintainers import canonicalize_actor, display_name_for


def test_laanwj_email_variants_collapse():
    emails = [
        "laanwj@gmail.com",
        "laanwj@protonmail.com",
        "Wladimir.J.vanderLaan@gmail.com",
        "126646+laanwj@users.noreply.github.com",
    ]
    keys = {canonicalize_actor(email=email) for email in emails}
    assert keys == {"laanwj"}


def test_laanwj_name_variants_collapse():
    names = [
        "Wladimir J. van der Laan",
        "W. J. van der Laan",
        "W.J. van der Laan",
        "laanwj",
    ]
    keys = {canonicalize_actor(name=name) for name in names}
    assert keys == {"laanwj"}
    assert display_name_for("laanwj") == "Wladimir J. van der Laan"


def test_unknown_email_is_not_invented():
    assert canonicalize_actor(email="nobody@example.com") == "nobody@example.com"


def test_irc_nicks_collapse_without_merging_github_logins():
    from src.utils.maintainers import canonicalize_nick, normalize_login, load_maintainer_login_set

    assert canonicalize_nick("wumpus") == "laanwj"
    assert canonicalize_nick("@wumpus") == "laanwj"
    assert canonicalize_nick("MarcoFalke") == "maflcko"
    assert canonicalize_nick("MacroFake") == "maflcko"
    assert canonicalize_nick("TheCharlatan") == "sedited"
    assert normalize_login("TheCharlatan") == "thecharlatan"
    maintainers = load_maintainer_login_set()
    assert "thecharlatan" in maintainers
    assert "sedited" in maintainers


def test_bip_preamble_name_variants_collapse():
    assert canonicalize_actor(name="karl-johan alm") == canonicalize_actor(name="kalle alm") == "kallewoof"
    assert canonicalize_actor(name="gregory sanders") == canonicalize_actor(name="greg sanders") == "instagibbs"
    assert display_name_for("kallewoof") == "Karl-Johan Alm"
