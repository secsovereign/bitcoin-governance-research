"""Tests for the Satoshi archive collector's authorship filter and correspondent archives.

Fixtures are small excerpts of the published archives; no network access is needed.
"""

import zipfile
from pathlib import Path

import pytest

from scripts.data_collection import satoshi_archive_collector as sac

ROOT = Path(__file__).parent.parent
ARCHIVE = ROOT / 'data' / 'satoshi_archive' / 'nakamoto-archive'
FIXTURES = Path(__file__).parent / 'fixtures' / 'satoshi_archive'


@pytest.fixture
def collector():
    """Collector bound to the vendored nakamoto-archive tree, without touching data/."""
    instance = sac.SatoshiArchiveCollector.__new__(sac.SatoshiArchiveCollector)
    instance.github_archive_dir = ARCHIVE
    return instance


# ── GitHub archive (lugaxker/nakamoto-archive) ──

def test_hal_finney_email_to_satoshi_is_dropped(collector):
    # From: hal@finney.org, To: Satoshi Nakamoto, 9 Jan 2009. Returned as a Satoshi cite on 2026-11-12.
    path = ARCHIVE / 'doc' / 'hal-finney' / '4.md'
    assert 'From: hal@finney.org' in path.read_text()
    assert collector._parse_github_archive_file(path, 'doc') is None


@pytest.mark.parametrize('relative', [
    'doc/hal-finney/3.md',             # From: "Satoshi Nakamoto" <satoshi@vistomail.com>
    'doc/hal-finney/2.md',             # no header, signed "Satoshi"
    'doc/adam-back/1.md',              # From: satoshi@anonymousspeech.com
    'doc/bitcoin-list/23824064.md',    # From: Satoshi Nakamoto <satoshin@gmx.com>
    'doc/bitcoin-forum/0005-00028.md', # Post by: satoshi
])
def test_satoshi_documents_are_kept(collector, relative):
    comm = collector._parse_github_archive_file(ARCHIVE / relative, 'doc')
    assert comm is not None
    assert comm['source'] == 'github_archive'


@pytest.mark.parametrize('relative', [
    'doc/hal-finney/6.md',   # From: Hal Finney <hal.finney@gmail.com>
    'doc/hal-finney/20.md',  # Hal's reply; a second From line names Satoshi
    'doc/adam-back/2.md',    # From: "Adam Back"
    'doc/wei-dai/2.md',      # From: "Wei Dai"
])
def test_correspondent_documents_are_dropped(collector, relative):
    assert collector._parse_github_archive_file(ARCHIVE / relative, 'doc') is None


def test_vendored_doc_tree_keeps_only_satoshi(collector):
    # Counts match the per-folder Satoshi counts in nakamoto-archive/README.md.
    kept = {}
    for path in sorted((ARCHIVE / 'doc').rglob('*.md')):
        if collector._parse_github_archive_file(path, 'doc'):
            kept[path.parent.name] = kept.get(path.parent.name, 0) + 1
    assert kept['hal-finney'] == 18
    assert kept['adam-back'] == 3
    assert kept['wei-dai'] == 2
    assert kept['bitcoin-list'] == 15
    assert kept['bitcoin-forum'] == len(list((ARCHIVE / 'doc' / 'bitcoin-forum').glob('*.md')))


def test_quote_or_recipient_is_not_authorship():
    assert not sac.document_is_satoshi('# Re: x\nPost by: theymos on July 1, 2010\n\nQuote from: satoshi on June 30, 2010\n> text\n')
    assert not sac.document_is_satoshi('# Re: x\n\nFrom: hal@finney.org<br>\nTo: Satoshi Nakamoto <satoshi@vistomail.com\\><br>\n\nHi\n')
    assert not sac.is_satoshi_author('Martti Malmi <mmalmi@cc.hut.fi>')
    assert sac.is_satoshi_author('"Satoshi Nakamoto" <satoshi@vistomail.com>')
    assert sac.is_satoshi_author('satoshi on November 22, 2009, 06:04:28 PM')


# ── Martti Malmi ──

def test_malmi_keeps_only_satoshi_emails():
    comms = sac.parse_malmi_html((FIXTURES / 'malmi_excerpt.html').read_text())
    assert [c['url'] for c in comms] == ['https://mmalmi.github.io/satoshi/#email-1']
    comm = comms[0]
    assert comm['source'] == 'malmi'
    assert 'satoshin@gmx.com' in comm['from']
    assert comm['content'].startswith('Thanks for starting that topic on ASC')
    assert "I'm Trickstern" not in comm['content']  # Martti's quoted text is stripped


# ── Mike Hearn ──

def test_hearn_keeps_only_satoshi_messages():
    url = 'https://plan99.net/~mike/satoshi-emails/thread2.html'
    comms = sac.parse_hearn_thread_html((FIXTURES / 'hearn_thread2.html').read_text(), url)
    assert len(comms) == 1
    comm = comms[0]
    assert comm['source'] == 'hearn'
    assert comm['url'] == url + '#message-2'
    assert comm['from'] == 'Satoshi Nakamoto <satoshin@gmx.com>'
    assert comm['subject'] == 'Lack of chargeback support'
    assert 'Quoted text hidden' not in comm['content']


# ── Dustin Trammell ──

def test_trammell_keeps_only_satoshi_and_dedupes(tmp_path):
    zip_path = tmp_path / 'Satoshi_Nakamoto.zip'
    with zipfile.ZipFile(zip_path, 'w') as archive:
        for mbox in sorted((FIXTURES / 'trammell').glob('*.mbox')):
            archive.write(mbox, f'Satoshi_Nakamoto/Email/{mbox.name}')
    comms = sac.parse_trammell_archive(zip_path)
    # Four mailboxes: one from Dustin, three from Satoshi, two of those the same
    # Message-ID (delivered directly and via the cryptography list).
    assert len(comms) == 2
    assert all(c['source'] == 'trammell' for c in comms)
    assert all('satoshi@vistomail.com' in c['from'] for c in comms)
    assert all(c['url'] == 'https://blog.dustintrammell.com/i-am-not-satoshi/' for c in comms)
    assert len({c['message_id'] for c in comms}) == 2
    assert comms[0]['content'].startswith("Thanks, I hadn't seen that yet.")


def test_correspondent_collectors_accept_local_paths(collector):
    assert len(collector._collect_malmi(str(FIXTURES / 'malmi_excerpt.html'))) == 1
    assert len(collector._collect_trammell(str(FIXTURES / 'trammell'))) == 2
