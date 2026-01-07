# Satoshi Nakamoto Governance Analysis

**Analysis Date:** 2026-01-07 17:23:23
**Total Communications Analyzed:** 549

## Executive Summary

- **Governance Mentions:** 292 communications
- **Decision Statements:** 154 instances
- **Authority Statements:** 14 instances
- **Community Interactions:** 461 communications
- **Protocol Discussions:** 187 communications
- **Key Governance Moments:** 51 identified

## Communication Patterns

### By Year
- **2009:** 2 communications
- **2010:** 2 communications
- **2015:** 2 communications

### By Type
- **unknown:** 545
- **email:** 3
- **forum_post:** 1

### Top Recipients
- **hal@finney.org:** 2 communications
- **weidai@ibiblio.org:** 1 communications

### 1. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

The average total coins generated across the network per day stays the same. &nbsp;Faster machines just get a larger share than slower machines. &nbsp;If everyone bought faster machines, they wouldn't get more coins than before.

We should have a gentleman's agreement to postpone the GPU arms race 
```

### 2. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

Uploaded some UI changes to SVN as version 0.2.5.

Instead of View->Show Generated, we now have tabs:
\- All Transactions
\- Sent/Received
\- Sent
\- Received

Makes it a lot easier to flip to received and check for payments.

Moved the "Your Addresses" book inside the main address book. &nbsp;It w
```

### 3. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

A second version would be a massive development and maintenance hassle for me. &nbsp;It's hard enough maintaining backward compatibility while upgrading the network without a second version locking things in. &nbsp;If the second version screwed up, the user experience would reflect badly on both, a
```

### 4. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: June 26, 2010, 12:14:27 AM by satoshi

Here's RC1 for linux for testing:
(link removed, see below)

It contains both 32-bit and 64-bit binaries.

Recent changes:

build-unix.txt:
\- Added instructions for building wxBase, which is needed to compile bitcoind.
\- The package libboost-dev do
```

### 5. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: June 25, 2010, 03:00:14 AM by satoshi

I don't know. &nbsp;Maybe someone with more Linux experience knows how to install the library it needs.

I built it on Ubuntu 10.04. &nbsp;I hope that wasn't a mistake. &nbsp;Maybe it should have been built on an older version for more backward compa
```

### 6. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: July 02, 2010, 09:56:11 PM by satoshi

Changed the version number to 1.3 and removed "Beta".

(links removed, see below)

Uses irc.lfnet.org.

---

Source file: bitcoin-forum-satoshi-nakamoto.tgz

External link: https://bitcointalk.org/index.php?topic=199.msg1806#msg1806

```

### 7. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

Quote from: llama on July 01, 2010, 10:21:47 PM

> However, if something happened and the signatures were compromised (perhaps integer factorization is solved, quantum computers?), then even agreeing upon the last valid block would be worthless.

True, if it happened suddenly. &nbsp;If it happens g
```

### 8. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

OK, back to 0.3 then.

Please download RC4 and check it over as soon as possible. &nbsp;I'd like to release it soon.

http://www.bitcoin.org/smf/index.php?topic=199.msg1927#msg1927

Other than the version number change, which included changes in readme.txt and setup.nsi, I reduced the maximum numbe
```

### 9. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: July 02, 2010, 10:33:43 PM by satoshi

I reduced max outbound connections from 15 to 8 in RC4.

15 was way more than we needed for redundancy. &nbsp;8 is still plenty of redundancy.

As the nodes upgrade to this version, this will cut in half the number of connections that inbound accepti
```

### 10. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

After it initially tries incorrectly to set itself to the lowest priority, the generate thread only changes its priority again temporarily when it finds a block. &nbsp;When you've found a block, you should want it to hurry up and broadcast it as soon a possible before someone else finds one and mak
```

### 11. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: July 16, 2010, 09:00:42 PM by satoshi

This is a bugfix maintenance release. &nbsp;It is now uploaded to SourceForge. &nbsp;Mac OS X didn't need any fixes so we don't really need to update it, 0.3.0 is still good.

The download links are on bitcoin.org

Changes:
\- Added Portuguese transl
```

### 12. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

Quote from: NewLibertyStandard on July 17, 2010, 10:22:09 PM

> Version 0.3 was supposed to reduce the number of outgoing connections on non-port forwarded clients from 15 to 8, but I don't think it really happened. I'm not positive if this is the case. Correct me if I'm wrong.

In 0.3.0, the chang
```

### 13. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: July 17, 2010, 11:46:13 PM by satoshi

Download links available now on bitcoin.org. &nbsp;Everyone should upgrade to this version.

\- Added a simple security safeguard that locks-in the block chain up to this point.
\- Reduced addr messages to save bandwidth now that there are plenty of 
```

### 14. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

The change list is basically encompassed by what's listed in the first message. &nbsp;Everyone should upgrade to get the important security improvements.

Minimizing to tray had at least 3 different glitches and bugs on Linux, including a crash one, so I disabled it again. &nbsp;You can still re-en
```

### 15. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

FLATDATA was a workaround to serialize a fixed field length array. &nbsp;There was a cleaner way to make it understand how to serialize arrays directly, but MSVC6 couldn't do it and I wanted to keep compatibility with MSVC6 at that time. &nbsp;We don't support MSVC6 anymore because we use something
```

### 16. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

Please test 0.3.2.5 in preparation for the 0.3.3 release! &nbsp;This build is looking good and should be the one that goes into 0.3.3. &nbsp;I encourage you to go ahead and upgrade now if you're on Windows or Linux.

New features:
\- Gavin Andresen's HTTP authentication to secure JSON-RPC
\- 5x fas
```

### 17. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

Please upgrade to 0.3.3! &nbsp;Important security improvements were made in 0.3.2 and 0.3.3.

New features:
- Gavin Andresen's HTTP authentication to secure JSON-RPC
- 5x faster initial block download, under 30 minutes

---

Source file: bitcoin-forum-satoshi-nakamoto.tgz

External link: https://bi
```

### 18. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: July 27, 2010, 07:44:48 PM by satoshi

Quote from: BlackEye on July 25, 2010, 10:12:23 PM

> I was able to integrate the SHA256 functionality from Crypto++ 5.6.0 into Bitcoin. &nbsp;This is the fastest SHA256 yet using the SSE2 assembly code. &nbsp;Since Bitcoin was sending unaligned data
```

### 19. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```

Yeah, acutely aware that I should have stayed on 9.04 or 9.10. &nbsp;It's a lot more work to downgrade than upgrade and I've been squeezed for time. &nbsp;Ubuntu is the most popular distro, so I'm staying with that.

---

Source file: bitcoin-forum-satoshi-nakamoto.tgz

External link: https://bitco
```

### 20. 

- **Date:** None
- **Type:** protocol
- **Significance:** Protocol change discussion

**Excerpt:**
```
Last edit: October 04, 2010, 01:37:36 PM by satoshi

Please upgrade to 0.3.6 ASAP! &nbsp;We fixed an implementation bug where it was possible that bogus transactions could be displayed as accepted. &nbsp;Do not accept Bitcoin transactions as payment until you upgrade to version 0.3.6!

If you can't 
```

## Authority and Control Statements

### 1. 

- **Date:** None
- **Pattern:** `i (control|own|manage|maintain|run)`

**Excerpt:**
```

Hello there,

I'm a new bitcoin user, and plan on accepting bitcoin currency for 
web-hosting that I run, because it sounds cool.

The build requirements for the main bitcoin app look a little painful, 
t
```

### 2. 

- **Date:** None
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```
's semi-technical guide to Bitcoin
From: Andrew Moroz <amoroz@gm...> - 2013-07-19 02:23:26

Hello,

I wrote an intro to Bitcoin for people with a bit of computer science
knowledge.

I'd be curious for everyo
```

### 3. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400
- **Pattern:** `my (decision|choice|project|code|software)`

**Excerpt:**
```
omeone has other 
motives to prove a point, they&#39;ll just be proving a point I already concede.

My choice for the number of coins and distribution schedule was an 
educated guess.  It was a difficult choic
```

### 4. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```
.  If they run 
it and get no connections, they&#39;ll probably just give up.

Satoshi

Martti Malmi wrote:
&gt; Message body follows:
&gt; 
&gt; Hello,
&gt; 
&gt; I&#39;m Trickstern from the anti-state.com
```

### 5. 

- **Date:** None
- **Pattern:** `i (control|own|manage|maintain|run)`

**Excerpt:**
```
rolled by command line or JSON-RPC.

On Linux it needs libgtk2.0-0 installed, but does not need a GUI running. &nbsp;Hopefully gtk can be installed without having a windowing system installed.

The command
```

### 6. 

- **Date:** None
- **Pattern:** `i (control|own|manage|maintain|run)`

**Excerpt:**
```

Quote from: laszlo on June 14, 2010, 06:30:58 PM

> I run an IRC server you can use, it's fairly stable but it's not on redundant connections or anything. &n
```

### 7. 

- **Date:** None
- **Pattern:** `i (control|own|manage|maintain|run)`

**Excerpt:**
```

Quote from: hugolp on May 08, 2010, 10:38:51 AM

> When I run bitcoin it becomes very sluggish, almost unusable. When I stop bitcoin everything goes ok again. It
```

### 8. 

- **Date:** None
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```
know how to read them.

The design supports a tremendous variety of possible transaction types that I designed years ago. &nbsp;Escrow transactions, bonded contracts, third party arbitration, multi-party signat
```

### 9. 

- **Date:** None
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```
't know. &nbsp;Maybe someone with more Linux experience knows how to install the library it needs.

I built it on Ubuntu 10.04. &nbsp;I hope that wasn't a mistake. &nbsp;Maybe it should have been built on an
```

### 10. 

- **Date:** None
- **Pattern:** `my (decision|choice|project|code|software)`

**Excerpt:**
```
nce I'm pretty close to making bitcoind build w/o wxBase. &nbsp;(it'll be in init.cpp)

Sorry about my choice of the filename "main.cpp", another possible name would have been "core.cpp". &nbsp;It's much too l
```

### 11. 

- **Date:** None
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```
&nbsp;The one we have is the only one I tried, so there's significant chance for improvement.

When I wrote it more than 2 years ago, there were screaming hot SHA1 implementations but minimal attention to SH
```

### 12. 

- **Date:** None
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```
e within 2000 blocks of the latest block, these changes turn off and it slows down to the old way.

I built a test build if you'd like to start using it:

http://www.bitcoin.org/download/bitcoin-0.3.2.5-win3
```

### 13. 

- **Date:** None
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```

I hope someone can test an i5 or AMD to check that I built it right. &nbsp;I don't have either to test with.

I'm also curious if it performs much worse on 32
```

### 14. 

- **Date:** None
- **Pattern:** `i (created|designed|built|wrote)`

**Excerpt:**
```

I just uploaded a quick build so testers can check if I built it right. &nbsp;(I don't have an i5 or AMD) &nbsp;If it checks out, I'll put together the full pack
```

## Decision-Making Statements

### 1. Re: Bitcoin v0.1

- **Date:** Sat, 10 Jan 2009 00:43:01 +0800

**Excerpt:**
```
thing.  If you have any questions, feel free.

>Hi, Satoshi, thanks very much for that information! I should have a cha-
nce
>to look at that this weekend. I am looking forward to learning more abo-
ut
>the c
```

### 2. 

- **Date:** None

**Excerpt:**
```
eturn NULL;<br />&nbsp; &nbsp; &nbsp; &nbsp; // FAT32 filesize max 4GB, fseek and ftell max 2GB, so we must stay under 2GB<br />&nbsp; &nbsp; &nbsp; &nbsp; if (ftell(file) &lt; 0x7F000000 - MAX_SIZE)<br />&n
```

### 3. 

- **Date:** None

**Excerpt:**
```
 CWalletDB().WriteTx(GetHash(), *this);<br />&nbsp; &nbsp; }<br /><br /><br />&nbsp; &nbsp; void AddSupportingTransactions(CTxDB&amp; txdb);<br />&nbsp; &nbsp; void AddSupportingTransactions() { CTxDB txdb(&
```

### 4. 

- **Date:** None

**Excerpt:**
```
ode could create a transaction with
an extra hash in it of anything that needs to be timestamped.  
I should add a command to timestamp a file that way.

> > > Later I want to add interfaces to make it reall
```

### 5. 

- **Date:** None

**Excerpt:**
```
Ret)
             nFileRet = nCurrentBlockFile;
             return file;
         }
+        // If we need to rotate to a new block file, the commit thread
+        // may not be able to sync the old file. So 
```

### 6. 

- **Date:** None

**Excerpt:**
```
.  Currently it only starts one
thread.  If you have a multi-core processor like a Core Duo or
Quad this will double or quadruple your production.

Later I want to add interfaces to make it really easy to inte
```

### 7. 

- **Date:** None

**Excerpt:**
```
 well as the
relevant transactions, you are only protected from someone spending
your coins.

It is recommended that you backup your wallet file before you
encrypt your wallet.  To do this, close the Bitcoin c
```

### 8. 

- **Date:** None

**Excerpt:**
```
t 4 years: 2,625,000 coins
next 4 years: 1,312,500 coins
etc...

When that runs out, the system can support transaction fees if
needed.  It's based on open market competition, and there will
probably always 
```

### 9. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400

**Excerpt:**
```
 code could create a transaction with
an extra hash in it of anything that needs to be timestamped.
I should add a command to timestamp a file that way.

 From a thread on p2presearch which starts with m
```

### 10. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400

**Excerpt:**
```
 anymore until we&#39;re closer to 
ready to start.  I think we&#39;ll get flooded with newbies and we need to 
get ready first.

What we need most right now is website writing.  My writing is not that 
great, 
```

### 11. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400

**Excerpt:**
```
 using your money more difficult for 
&gt; someone who happens to find your key file.

Definitely.  This will be an absolutely essential feature once things 
get going, making it so you can lock your wealth up
```

### 12. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400

**Excerpt:**
```
FAQ. I&#39;ll start writing the  
FAQ now with the questions that I can think of.

I have a feature suggestion for the program: a UI tool for creating  
password protected private keys and saving them into a
```

### 13. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400

**Excerpt:**
```
to unlock it, there&#39;s no way to get your coins back. If
you have a large amount of coins, it is recommended to distribute
them under several keys. You propably wouldn&#39;t either keep all
your dollars or 
```

### 14. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400

**Excerpt:**
```
e trust model.  In its
central position, the company can override the users, and the fees
needed to support the company make micropayments impractical.

Bitcoin&#39;s solution is to use a peer-to-peer networ
```

### 15. Citation of your b-money page

- **Date:** None

**Excerpt:**
```
ete working system.
Adam Back (hashcash.org) noticed the similarities and pointed me to your
site.

I need to find out the year of publication of your b-money page for the
citation in my paper.  It'll look lik
```

## Protocol and Technical Discussions

### 1. Re: Bitcoin v0.1

- **Date:** Sat, 10 Jan 2009 00:43:01 +0800

**Excerpt:**
```
From satoshi@vistomail.com Fri Jan 9 08:08:37 2009
Return-Path: <satoshi@vistomail.com>
X-Original-To: hal@finney.org
Delivered-To: hal@finney.org
Received: from mail.anonymous speech.com (anonymousspeech.com [124.217.253.421)
        by finney.org (Postfix) with ESMTP id 220A414F6E1
        for <hal@finney.org>; Fri, 9 Jan 2009 08:08:35 -0800 (PST)
Received: from server123 ([124.217.253.42]) by a
```

### 2. Bitcoin v0.1

- **Date:** Fri, 09 Jan 2009 13:21:04 +0800

**Excerpt:**
```
From satoshi@vistomail.com Thu Jan 8 20:54:55 2009
Return-Path: <satoshi@vistomail.com>
X-Original-To: hal@finney.org
Delivered-To: hal@finney.org
Received: from mail.anonymousspeech.com (anonymous speech.com [124.217.253.421)
        by finney.org (Postfix) with ESMTP id 467AA14F6E1
        for <ha18finney.org>; Thu, 8 Jan 2009 20:54:53 -0800 (PST)
Received: from server123 ([124.217.253.421) by a
```

### 3. 

- **Date:** None

**Excerpt:**
```
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1" />
		<link rel="canonical" href="https://bitcointalk.org/index.php?topic=382374.0" />
		<title>Print Page - Bitcoin source from November 2008.</title>
	
```

### 4. 

- **Date:** None

**Excerpt:**
```
Bitcoin mailing list archives (2008-2015)

Retrieved from http://sourceforge.net/p/bitcoin/mailman/bitcoin-list/?viewmonth=AAAAMM using Internet Archive (web.archive.org) on May 6, 2022

---

[bitcoin-list] Welcome
From: Satoshi Nakamoto <satoshi@vi...> - 2008-12-10 17:00:23

Welcome to the Bitcoin mailing list!

---

[bitcoin-list] Crash in bitcoin 0.1.0
From: Hal Finney <hal.finney@gm...> - 2009
```

### 5. Re: Introduction

- **Date:** Thursday, March 4, 2010, 9:55 PM

**Excerpt:**
```
Jon Matonis
Executive Director

Members
Pip
56 posts
Posted 22 December 2012 - 11:04 AM

Thanks for sharing that, Gavin and Mike. It made me go back and look for my Satoshi correspondence, which unfortunately has been purged except for my last email from Satoshi on 4th March 2010. We went back and forth a bit on how bitcoin was an evolution over issuing mint functionality like Chaum's DigiCash an
```

### 6. Re: bitcoin!!!!

- **Date:** Wed, 14 Jul 2010 10:56:21 -0400

**Excerpt:**
```
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Satoshi - Sirius emails 2009-2011</title>
    <style>
      body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f9f9f9; }
      .message { border-bottom: 1px solid #ddd; padding-bottom: 20px; margin-bottom: 20px; padding: 10px; background-color: #ffffff; }
      .message.sirius { border-left: 2
```

### 7. Citation of your b-money page

- **Date:** None

**Excerpt:**
```
Emails between Satoshi Nakamoto and Wei Dai (2008-2009)

Retrieved from https://gwern.net/doc/bitcoin/2008-nakamoto

---

From: "Satoshi Nakamoto" <satoshi@anonymousspeech.com>
Sent: Friday, August 22, 2008 4:38 PM
To: "Wei Dai" <weidai@ibiblio.org>
Cc: "Satoshi Nakamoto" <satoshi@anonymousspeech.com>
Subject: Citation of your b-money page

I was very interested to read your b-money page.  I'm get
```

### 8. 

- **Date:** None

**Excerpt:**
```

There will be a proxy setting in version 0.2 so you can connect through TOR. &nbsp;I've done a careful scrub to make sure it doesn't use DNS or do anything that would leak your IP while in proxy mode.

---

Source file: bitcoin-forum-satoshi-nakamoto.tgz

External link: https://bitcointalk.org/index.php?topic=7.msg32#msg32

```

### 9. 

- **Date:** None

**Excerpt:**
```

\> Can nodes on the network tell from which and or to which bitcoin
\> address coins are being sent? Do blocks contain a history of where
\> bitcoins have been transfered to and from?

Bitcoins are sent to and from bitcoin addresses, which are essentially random numbers with no identifying information.

When you send to an IP address, the transaction is still written to a bitcoin address. &nbsp;T
```

### 10. 

- **Date:** None

**Excerpt:**
```

\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-
scott:
Linux/UNIX compile
Posted:Thu 08 of Oct, 2009 (05:49 UTC)

Can we get instructions or modifications to compile and install BitCoin on Linux? A command line version would be great.

---

Source file: bitcoin-forum-satoshi-nakamoto.tgz

External link: https://bitcointalk.org/index.php?topic=9.msg36#msg36

```

### 11. 

- **Date:** None

**Excerpt:**
```

The Linux version is on its way. &nbsp;Martti's Linux port was merged into the main code branch and New Liberty Standard has been testing it. &nbsp;It'll be in the next release, version 0.2.

Command line is on the to-do list after 0.2.

---

Source file: bitcoin-forum-satoshi-nakamoto.tgz

External link: https://bitcointalk.org/index.php?topic=9.msg37#msg37

```

### 12. 

- **Date:** None

**Excerpt:**
```
Last edit: October 09, 2011, 07:33:02 PM by theymos

We've been working hard on improvements for the next version release. &nbsp;Martti (sirius-m) added some nice features to make it more user friendly and easier to run in the background:
&nbsp;\- Minimize to system tray option
&nbsp;\- Autostart on boot option so you can keep it running in the background automatically
&nbsp;\- New options dialog 
```

### 13. 

- **Date:** None

**Excerpt:**
```
Last edit: December 12, 2009, 03:33:02 PM by satoshi

Right, the SVN has the almost-release-candidate 0.2 source, which can also be built and run on Linux. &nbsp;&nbsp;It hasn't been tested on FreeBSD.

Quote from: madhatter2 on December 11, 2009, 04:59:19 AM

> If we can get to the point where we have a working backend process that will run on FreeBSD I can run always-on seeds.

That would be a b
```

### 14. 

- **Date:** None

**Excerpt:**
```

The average total coins generated across the network per day stays the same. &nbsp;Faster machines just get a larger share than slower machines. &nbsp;If everyone bought faster machines, they wouldn't get more coins than before.

We should have a gentleman's agreement to postpone the GPU arms race as long as we can for the good of the network. &nbsp;It's much easer to get new users up to speed if
```

### 15. 

- **Date:** None

**Excerpt:**
```
Last edit: December 14, 2009, 05:27:14 PM by satoshi

Quote from: madhatter2 on December 14, 2009, 03:01:39 PM

> Can anyone shed some light here?
>
> g++ -c -O0 -Wno-invalid-offsetof -Wformat -g -D\_\_WXMAC\_\_ -DNOPCH -DBUILD_MACOSX -I"/usr/include" -I"/usr/local/include/wx-2.8" -I"/usr/local/include" -I"/usr/local/boost_1_41_0" -I"/sw/include/db4" -I"/usr/local/ssl/include" -I"/usr/local/lib/wx
```

## Governance Keywords Frequency

- **change:** 98 mentions
- **node:** 92 mentions
- **network:** 77 mentions
- **client:** 49 mentions
- **upgrade:** 39 mentions
- **standard:** 27 mentions
- **power:** 20 mentions
- **improvement:** 20 mentions
- **trust:** 19 mentions
- **miner:** 18 mentions
- **compatibility:** 18 mentions
- **control:** 17 mentions
- **core:** 16 mentions
- **implementation:** 16 mentions
- **fork:** 12 mentions
- **protocol:** 5 mentions
- **rule:** 5 mentions
- **developer:** 5 mentions
- **specification:** 3 mentions
- **decentralized:** 3 mentions
