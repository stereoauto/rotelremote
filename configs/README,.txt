Notes:

This entire rotelRemote project was put together rather quickly as a proof of concept, its
implementation of the Rotel protocol is not exhaustive and the GUI is not meant to be pretty
or modern, it just needed to work.

This project lets you control a Rotel amp using a Python-based GUI running on a PC (pr any
other Python-enabled device).

Recommended setup:

 - the amp is accessed via an IPv4 address, so rour home network's DHCP server should have the
amp's MAC address set up to receive a fixed IP address so you don't need to keep changing the
address in this tool.

 - See notes below about EU market limitations and recommended power settings in the amp's firmware.

The general gist of Rotel's command language:

'Commands' change settings on the amp, they typically have a string followed by an exclamation
point, and can contain numeric values depending on the command.

Command examples:
   cd! - switch to CD input
   vol_up! - turn the voilume up by 1
   vol_45! - set the volume to 45
   balance_R05! - set the balance to 'right, +5'

The amplifier will respond to commands with the newly set value if it understood the command. It
can also respond with other configuration values that are affected by the change (for example, if
you switch to a digital input, the amp may respond with the new source name along with the current
frequency of that input).

'Queries' will read values from the amplifier's configuration - these are strings followed by a
question mark. The amp will respond with the item's name, an equal sign, and the value, followed
by a dollar sign ($) to mark the end of the value.

Query examples:
   source? - which source is active
   volume? - current volume setting
   bypass? - current tone bypass setting

There are documents on Rotel's website that describe an earlier version of their IP protocol, but I
found this was outdated for the v3.8 firmware on my A14 mkII.

Primarily, the docs that I found said that port 9590 is used for communication, but it turned out to
be 9596.

Also, the doc is missing the 'amp:' prefix for all of the amplifier's settings, I'm guessing that if
one also had a Rotel CD player connected to the amp along with a 'Rotel Link' connection, the protocol
could also soupport transport commands like play, pause, next, etc. - however, I just have the amp so
I haven't been able to test this part of the protocol.

Testing for this interface was done with a North American amplifier model. Note that the power commands
may not work in EU settings due to regulations that restrict the idle power consumption of electronics.
For the v3.08 firmware version, the 'Power Mode' for the amp had to be set to 'Quick' instead of 'Normal'
too be able to connect to the amp and bring it out of standby.

My initial config file for my Rotel A14 mk II with its interface on port 9596 is in
configs\Rotel_A14_mkii_fw3_08.json

For questions, comments, etc. - please feel free to contact the author via email:

ccbutler@gmail.com

...and if you're a Python GUI developer who can hack together a better-looking interface, let's talk.

Chris Butler Ottawa, Ontario, Canada