"""
Template-based modles to generate logs are implemented in this module.
"""

import datetime
import os
import random
import socket
import struct

from .models import BaseModel
from .models import choose_in_normal_distribution


def random_username():
    """
    Generates a random username.
    """
    names = ["MohammadReza", "AmirHosein", "Hedayat", "Mohammad", "Omid",
             "Hassan", "Payam", "AhmadReza", "SeyedMahdi", "Zahra", "Hoora",
             "Fatemeh", "Fateme", "Monire"]
    surnames = ["Arbanshirani", "Shamsi", "AliAkbarian", "Vatankhah", "Razavi",
                "Akbari", "Ahmadi", "Mohagheghian", "Nouri", "Esnaashari",
                "Mahdinia", "Noroozi", "Hajikarami", "Mirsadegh"]
    return "".join([random.choice(names), random.choice(surnames)])


class LogTemplateModel(BaseModel):
    """
    Base model class that facilitates sub-classes to generate logs
    according to a set of templates. Each log produced by `next`
    method is a `dict`.

    The sub-class must override the `templates` attribute with a list
    of dictionaries (templates). The `next` method will randomly
    select a template and uses a seed (i.e. a `dict`) to convert the
    template to the concrete value.

    The seed for each template will be created by first calling the
    __seed__ method. The default __seed__ (which could be overridden
    by the sub-classes) will randomly generate common log requirements
    like srcip, srcport, etc.

    The seed object can be later completed by `__seed__` and
    `__instance_seed__` items of the template. First `__seed__` (if
    exists) will be called with old seed as the only argument and then
    `__instance_seed__` (if exists) will be called by passing two
    arguments `self` and the old seed. The result of these calls must
    be a dictionary that will be merged into the old seed.

    The value of each item in the template dictionary will be rendered
    to the concrete value according to its data type:

      - callable: It will be called (with one argument: the seed
        dictionary) and the result will be used as the concrete value.

      - str (or any object with `format` method): The `.format`
        attribute will be called (with **seed as the keyword
        arguments).

      - other types: It will be used as-is.
    """

    templates = []
    enable_default_log_seeds = True

    def _random_ip(self, stddev=100):
        ip_int = choose_in_normal_distribution(
            -2 ** 31, 2 ** 31 - 1, stddev=stddev)
        ip_string = socket.inet_ntoa(struct.pack("!l", ip_int))
        return ip_int, ip_string

    def _random_valid_port(self):
        return random.choices(
            [21, 22, 23, 25, 80, 110, 220, 443],
            weights=[10, 5, 5, 5, 100, 5, 5, 20])[0]

    def _random_port(self, stddev=2, valid_port_probability=0.4):
        return self._random_valid_port() \
            if random.random() < valid_port_probability else \
            choose_in_normal_distribution(1, 32768, stddev=stddev)

    def __seed__(self, seed):
        default = {}

        if self.enable_default_log_seeds:
            # TODO: preserve "aid" value in consecutive executions
            default["aid"] = os.getpid()
            default["srcip_int"], default["srcip"] = self._random_ip()
            default["dstip_int"], default["dstip"] = self._random_ip()
            default["srcport"] = self._random_port()
            default["dstport"] = self._random_port()

        return {**seed, **default}

    def next(self):
        """
        Returns a dictionary by randomly selecting a template and
        using the seed value to convert it to a concrete value.
        """
        seed = self.__seed__({})

        # Select an item from templates according to their weights
        template = {**random.choices(self.templates,
                                     weights=self.templates_weights)[0]}

        template_seed = template.pop("__seed__", {})
        if callable(template_seed):
            seed.update(template_seed(seed))
        else:
            seed.update(template_seed)

        template_instance_seed = template.pop("__instance_seed__", {})
        if callable(template_instance_seed):
            seed.update(template_instance_seed(self, seed))
        else:
            seed.update(template_instance_seed)

        result = {key: (value(seed) if callable(value) else
                        value.format(**seed)
                        if callable(getattr(value, "format", None))
                        else value)
                  for key, value in template.items()}

        return result


def log_templates(obj):
    """
    A decorator for LogTemplateModel sub-classed which will update
    the class `templates` attribute.

    A set of default templates useful for logs (srcip, srcport, ...)
    will be added to each template.

    Also all the class attributes started with the prefix "all_" will
    be added to each template (without "all_" prefix).

    A "templates_weights" attribute i.e. a list of weights according
    to "__ratio__" key of each template in templates list will also be
    added to the decorated object and "__ratio__" keys will be removed
    from the template dictionaries.

    The decorator will always preserve a specific order for the items
    of the dictionary (CPython 3.6+).
    """
    defaults_base = {
        "aname": None, "aclass": None, "amodel": None, "aid": "{aid}",
        "severity": "low",
        "srcip": lambda seed: seed["srcip_int"],
        "srcport": lambda seed: seed["srcport"],
        "dstip": lambda seed: seed["dstip_int"],
        "dstport": lambda seed: seed["dstport"],
        "ident": None, "msg": None,
    }

    for template in obj.templates:
        defaults = {}

        # Add dunder magic attirbutes in the beginning of the
        # dictionary
        for attr in ["__ratio__", "__seed__"]:
            if attr in template:
                defaults[attr] = None

        defaults.update(defaults_base)

        for attr, value in obj.__dict__.items():
            if attr.startswith("all_"):
                defaults[attr[4:]] = value

        defaults.update(template)

        # To change order in Python 3.6+ dictionaries
        template.clear()
        template.update(defaults)

    obj.templates_weights = [template.pop("__ratio__", 1)
                             for template in obj.templates]

    return obj


@log_templates
class MikrotikPPTPModel(LogTemplateModel):
    __model_name__ = "mikrotik_pptp"
    all_aname = "MikroTik-PPTP-stub"
    all_aclass = "11"
    all_amodel = "4350"
    all_aid = "MikroTik-PPTP-stub-{aid}"
    all_severity = "low"

    def login_seed(self, seed):
        new_user = random_username()
        self.logged_in_users = getattr(self, "logged_in_users", set())
        self.logged_in_users.add(new_user)
        return {"username": new_user}

    def logout_seed(self, seed):
        try:
            username = self.logged_in_users.pop()
        except (AttributeError, KeyError):
            username = "unknown"
        return {"username": username}

    def random_user_seed(self, seed):
        return {"username": random_username()}

    templates = [
        {"__ratio__": 1, "__instance_seed__": login_seed,
         "ident": "pptp,ppp,info,account,login",
         "msg": "pptp,ppp,info,account  {username} logged in, {srcip}"},
        {"__ratio__": 1, "__instance_seed__": logout_seed,
         "ident": "pptp,ppp,info,account,logout",
         "msg": "pptp,ppp,info,account,logout  {username} logged out, 51207 62321664 2891092466 1296625 2110154"},
        {"__ratio__": 1, "__instance_seed__": random_user_seed,
         "ident": "pptp,ppp,error",
         "msg": "pptp,ppp,error  <31292>: user {username} authentication failed"},
        {"ident": "pptp,ppp,debug,packet",
         "msg": "pptp,ppp,debug,packet   <31290>: rcvd CCP ConfReq id=0x6",
         "username": "-"},
        {"ident": "pptp,debug,packet",
         "msg": "pptp,debug,packet  rcvd Echo-Request from {srcip}",
         "username": "-"},
        {"ident": "pptp,info",
         "msg": "pptp,info  TCP connection established from {srcip}",
         "username": "-"},
    ]


@log_templates
class PPTPModel(LogTemplateModel):
    __model_name__ = "pptp"
    all_aname = "PPTP-stub"
    all_aclass = "24"
    all_amodel = "315"
    all_aid = "PPTP-stub-{aid}"
    all_severity = "low"

    templates = [
        {"__ratio__": 1,
         "ident": "control connection finished",
         "msg": " CTRL: Client 172.16.15.17 control connection finished"},
        {"__ratio__": 1,
         "ident": "Reaping child",
         "msg": " CTRL: Reaping child PPP[15465]"},
        {"__ratio__": 1,
         "ident": "Starting call",
         "msg": " CTRL: Starting call (launching pppd, opening GRE)"},
        {"__ratio__": 1,
         "ident": "Ignored a SET",
         "msg": " CTRL: Ignored a SET LINK INFO packet with real ACCMs!"},
        {"__ratio__": 1,
         "ident": "read",
         "msg": " GRE: read(fd=6,buffer=8058f20,len=8196) from PTY failed: status = -1 error = Input/output error, usually caused by unexpected termination of pppd, check option syntax and pppd logs"},
        {"__ratio__": 1,
         "ident": "PTY read or GRE write failed",
         "msg": " CTRL: PTY read or GRE write failed (pty,gre)=(6,7)"},
    ]


@log_templates
class ASAModel(LogTemplateModel):
    __model_name__ = "asa"
    all_aname = "ASA-stub"
    all_aclass = "10"
    all_amodel = "302"
    all_aid = "ASA-stub-{aid}"
    all_severity = "low"

    templates = [
        {"__ratio__": 1,
         "ident": "106015",
         "msg": "%%ASA-6-106015: Deny TCP (no connection) from {srcip}/{srcport} to {dstip}/{dstport} flags FIN ACK  on interface inside"},
        {"__ratio__": 1,
         "ident": "302021",
         "msg": "%%ASA-6-302021: Teardown ICMP connection for faddr {srcip}/{srcport} gaddr {dstip}/{dstport} laddr {dstip}/{dstport}"},
        {"__ratio__": 1,
         "ident": "302020",
         "msg": "%%ASA-6-302020: Built inbound ICMP connection for faddr {srcip}/{srcport} gaddr %{dstip}/{dstport} laddr {dstip}/{dstport}"},
    ]


@log_templates
class ScreenOSModel(LogTemplateModel):
    __model_name__ = "screenon"
    all_aname = "ScreenOS-stub"
    all_aclass = "10"
    all_amodel = "373"
    all_aid = "ScreenOS-stub-{aid}"
    all_severity = "low"
    all_service = "{service}"
    all_proto = "6"
    all_src_zone = "{src_zone}"
    all_dst_zone = "{dst_zone}"
    all_action = "{action}"
    all_sent = "{sent}"
    all_rcvd = "{rcvd}"

    def __seed__(self, seed):
        seed = super().__seed__(seed)
        seed["policy_id"] = random.randint(1000, 9999)
        seed["service"] = random.choice(["https", "tcp/port:4007"])
        seed["src_zone"] = random.choice(["Trust", "Untrust"])
        seed["dst_zone"] = random.choice(["Trust", "Untrust"])
        seed["action"] = random.choice(["Permit", "Deny"])
        seed["sent"] = random.randint(0, 1024)
        seed["rcvd"] = random.randint(0, 1024)
        seed["src_xlated_ip"] = ".".join(str(random.randrange(0, 256))
                                         for _ in range(4))
        seed["src_xlated_port"] = random.randrange(0, 65536)
        seed["dst_xlated_ip"] = ".".join(str(random.randrange(0, 256))
                                         for _ in range(4))
        seed["dst_xlated_port"] = random.randrange(0, 65536)
        seed["session_id"] = random.randint(0, 999999)
        seed["reason"] = random.choice(["Traffic Denied", "Creation"])
        return seed

    templates = [
        {"__ratio__": 1,
         "ident": "system-notification-00257-Deny",
         "msg": 'NetScreen device_id=APT1-Force2  [Root]system-notification-00257(traffic): start_time="2017-07-08 11:18:22" duration=0 policy_id={policy_id} service={service} proto=6 src zone={src_zone} dst zone={dst_zone} action={action} sent={sent} rcvd={rcvd} src={srcip} dst={dstip} src_port={srcport} dst_port={dstport} session_id={session_id} reason={reason}'},
        {"__ratio__": 1,
         "ident": "system-notification-00257-Permit",
         "msg": 'NetScreen device_id=APT1-Force2  [Root]system-notification-00257(traffic): start_time="2017-07-08 11:18:21" duration=0 policy_id={policy_id} service={service} proto=6 src zone={src_zone} dst zone={dst_zone} action={action} sent={sent} rcvd={rcvd} src={srcip} dst={dstip} src_port={srcport} dst_port={dstport} src-xlated ip={src_xlated_ip} port={src_xlated_port} dst-xlated ip={dst_xlated_ip} port={dst_xlated_port} session_id={session_id} reason={reason}',
         "src_xlated_ip": "{src_xlated_ip}",
         "dst_xlated_ip": "{dst_xlated_ip}",
         "src_xlated_port": "{src_xlated_port}",
         "dst_xlated_port": "{dst_xlated_port}"},
    ]


@log_templates
class FortigateModel(LogTemplateModel):
    __model_name__ = "fortigate"
    all_aname = "Fortigate-stub"
    all_aclass = "10"
    all_amodel = "360"
    all_aid = "Fortigate-stub-{aid}"
    all_severity = "low"
    all_srccountry = "{srccountry}"
    all_dstcountry = "{dstcountry}"
    all_devname = "{devname}"
    all_devid = "FG3K6A3102500907"
    all_type = "{type}"
    all_subtype = "{subtype}"

    def __seed__(self, seed):
        seed = super().__seed__(seed)

        now = datetime.datetime.now()
        countries = ["Reserved", "United States", "Iran, Islamic Republic of",
                     "Thailand", "China"]

        seed["date"] = now.strftime("%Y-%m-%d")
        seed["time"] = now.strftime("%H:%M:%S")
        seed["devname"] = random.choice(["FG-RR-Master", "FG-RR-Backup"])
        seed["type"] = random.choice(["traffic", "app-ctrl"])
        seed["subtype"] = ("app-ctrl" if seed["type"] == "app-ctrl" else
                           random.choice(["allowed", "violation", "other"]))
        seed["pri"] = random.choice(["notice", "information", "warning"])
        seed["vd"] = random.choice(["root", "Internet", "VPN"])
        seed["status"] = random.choice(["accept", "deny", "start"])
        seed["sent"] = random.randint(0, 1024)
        seed["rcvd"] = random.randint(0, 1024)
        seed["srccountry"] = random.choice(countries)
        seed["dstcountry"] = random.choice(countries)
        return seed

    templates = [
        {"__ratio__": 1,
         "ident": "0021000002",
         "msg": 'date={date}  time={time} devname={devname} device_id=FG3K6A3102500907 log_id=0021000002 type={type} subtype={subtype} pri={pri} vd={vd} src={srcip} src_port={srcport} src_int="Int-40" dst={dstip} dst_port={dstport} dst_int="Int-176" SN=2713976254 status=accept policyid=67 dst_country="{dstcountry}" src_country="{srccountry}" dir_disp=org tran_disp=noop service=HTTPS proto=6 duration=6 sent={sent} rcvd={rcvd} sent_pkt=1 rcvd_pkt=0'},
        {"__ratio__": 1,
         "ident": "0038000004",
         "msg": 'date={date}  time={time} devname={devname} device_id=FG3K6A3102500907 log_id=0038000004 type={type} subtype={subtype} pri={pri} vd={vd} src={srcip} src_port={srcport} src_int="Int-40" dst={dstip} dst_port={dstport} dst_int="Int-176" SN=2713992844 status=start policyid=87 dst_country="{dstcountry}" src_country="{srccountry}" service=HTTPS proto=6 duration=0 sent={sent} rcvd={rcvd}'},
        {"__ratio__": 1,
         "ident": "1059028704",
         "msg": 'date={date}  time={time} devname={devname} device_id=FG3K6A3102500907 log_id=1059028704 type={type} subtype={subtype} pri={pri} vd={vd} attack_id=41540 user="N/A" group="N/A" src={srcip} src_port={srcport} src_int="Int-176" dst={dstip} dst_port={dstport} dst_int="Int-40" src_name="{srcip}" dst_name="{dstip}" profilegroup="N/A" profiletype="N/A" profile="N/A" proto=6 service="https" policyid=87 intf_policyid=0 identidx=0 serial=2713992714 app_list="R-Access-Block" app_type="Network.Service" app="SSL_TLSv1.2" action=pass count=1 hostname="www.ir" url="/" msg="Network.Service: SSL_TLSv1.2, "'},
        {"__ratio__": 1,
         "ident": "0038000007",
         "msg": 'date={date}  time={time} devname={devname} device_id=FG3K6A3102500907 log_id=0038000007 type={type} subtype={subtype} pri={pri} vd={vd} src={srcip} src_port={srcport} src_int="Int-176" dst={dstip} dst_port={dstport} dst_int=unknown-0 SN=0 status=deny policyid=0 dst_country="{dstcountry}" src_country="{srccountry}" service=14672/tcp proto=6 duration=10992175 sent={sent} rcvd={rcvd} msg="no session matched"'},
        {"__ratio__": 1,
         "ident": "0038000005",
         "msg": 'date={date}  time={time} devname={devname} device_id=FG3K6A3102500907 log_id=0038000005 type={type} subtype={subtype} pri={pri} vd={vd} src={srcip} src_port={srcport} src_int="port1" dst={dstip} dst_port={dstport} dst_int="172.16.44-test" SN=2713983813 status=accept policyid=1 dst_country="{dstcountry}" src_country="{srccountry}" dir_disp=org tran_disp=noop service=3/3/icmp proto=1 duration=10992175 sent={sent} rcvd={rcvd} sent_pkt=0 rcvd_pkt=0'},
        {"__ratio__": 1,
         "ident": "0022000003",
         "msg": 'date={date}  time={time} devname={devname} device_id=FG3K6A3102500907 log_id=0022000003 type={type} subtype={subtype} pri={pri} vd={vd} src={srcip} src_port={srcport} src_int="Int-40" dst={dstip} dst_port={dstport} dst_int="Int-176" SN=2713992856 status=deny policyid=314 dst_country="{dstcountry}" src_country="{srccountry}" service=TELNET proto=6 duration=0 sent={sent} rcvd={rcvd}'},
        {"__ratio__": 1,
         "ident": "0038000006",
         "msg": 'date={date}  time={time} devname={devname} device_id=FG3K6A3102500907 log_id=0038000006 type={type} subtype={subtype} pri={pri} vd={vd} src={srcip} src_port={srcport} src_int="Int-176-VPN" dst={dstip} dst_port={dstport} dst_int=unknown-0 SN=0 status=deny policyid=0 dst_country="{dstcountry}" src_country="{srccountry}" service=3/1/icmp proto=1 duration=10992175 sent={sent} rcvd={rcvd} msg="no protocol tuple found, drop.'},
        ]

@log_templates
class SnortModel(LogTemplateModel):
    __model_name__ = "snort"
    all_aname = "Snort-stub"
    all_aclass = "1"
    all_amodel = "1"
    all_aid = "Snort-stub-{aid}"
    all_severity = "high"
    all_ident = "{ident}"
    all_msg = "[{ident}:1] {clstext} [Priority: 3] (TCP) {srcip}:{srcport} -> {dstip}:{dstport}"
    all_clstext = "{clstext}"
    all_proto = "TCP"

    def __seed__(self, seed):
        seed = super().__seed__(seed)
        seed["ident"], seed["clstext"] = random.choice(self._templates)
        return seed

    templates = [{"__ratio__": 1}]

    _templates = [
        ("1:2100483", "GPL SCAN PING CyberKit 2.2 Windows"),
        ("1:2101893", "GPL SNMP missing community string attempt"),
        ("1:1411", "GPL SNMP public access udp"),
        ("1:2003494", "ET POLICY AskSearch Toolbar Spyware User-Agent (AskTBar)"),
        ("1:2101918", "GPL SCAN SolarWinds IP scan attempt"),
        ("1:2000334", "ET P2P BitTorrent peer sync"),
        ("1:2011716", "ET SCAN Sipvicious User-Agent Detected (friendly-scanner)"),
        ("1:2009475", "ET POLICY TeamViewer Dyngate User-Agent"),
        ("1:2007994", "ET MALWARE User-Agent (1 space)"),
        ("1:2101892", "GPL SNMP null community string attempt"),
        ("1:2802973", "ETPRO TROJAN Yahlover Checkin Request (setting.doc)"),
        ("1:2012200", "ET CURRENT_EVENTS Possible Worm W32.Svich or Other Infection Request for setting.doc"),
        ("1:2802974", "ETPRO TROJAN Yahlover Checkin Request (setting.xls)"),
        ("1:2012199", "ET CURRENT_EVENTS Possible Worm W32.Svich or Other Infection Request for setting.xls"),
        ("1:2001330", "ET POLICY RDP connection confirm"),
        ("1:2001329", "ET POLICY RDP connection request"),
        ("1:2001331", "ET POLICY RDP disconnect request"),
        ("1:2013911", "ET TROJAN P2P Zeus or ZeroAccess Request To CnC"),
        ("1:2012183", "ET SCAN Possible Open SIP Relay scanner Fake Eyebeam User-Agent Detected"),
        ("1:2010164", "ET TROJAN Daonol C&C Communication"),
        ("1:2009024", "ET TROJAN Downadup/Conficker A or B Worm reporting"),
        ("1:2013912", "ET TROJAN P2P Zeus Response From CnC"),
        ("1:2010144", "ET P2P Vuze BT UDP Connection (5)"),
        ("1:2013505", "ET POLICY GNU/Linux YUM User-Agent Outbound likely related to package management"),
        ("1:2000357", "ET P2P BitTorrent Traffic"),
        ("1:2010785", "ET CHAT Facebook Chat (buddy list)"),
        ("1:2011495", "ET CURRENT_EVENTS Executable Download named to be .com FQDN"),
        ("1:2001569", "ET SCAN Behavioral Unusual Port 445 traffic, Potential Scan or Infection"),
        ("1:2801347", "ETPRO TROJAN Mariposa or Palevo Bot Checkin to Server"),
        ("1:2013504", "ET POLICY GNU/Linux APT User-Agent Outbound likely related to package management"),
        ("1:2013497", "ET TROJAN MS Terminal Server User A Login, possible Morto inbound"),
        ("1:2012735", "ET POLICY Babylon User-Agent (Translation App Observed in PPI MALWARE)"),
        ("1:2001219", "ET SCAN Potential SSH Scan"),
        ("1:2000328", "ET POLICY Outbound Multiple Non-SMTP Server Emails"),
        ("1:2008795", "ET POLICY TeamViewer Keep-alive inbound"),
        ("1:2001579", "ET SCAN Behavioral Unusual Port 139 traffic, Potential Scan or Infection"),
        ("1:1419", "GPL SNMP trap udp"),
        ("1:2010937", "ET POLICY Suspicious inbound to mySQL port 3306"),
        ("1:2010140", "ET P2P Vuze BT UDP Connection"),
        ("1:100000233", "GPL CHAT Jabber/Google Talk Outoing Message"),
        ("1:2014635", "ET TROJAN Possible Variant.Kazy.53640 Malformed Client Hello SSL 3.0 (Cipher_Suite length greater than Client_Hello Length)"),
        ("1:2012730", "ET CURRENT_EVENTS Known Hostile Domain ilo.brenz.pl Lookup"),
        ("1:2014634", "ET TROJAN Possible Variant.Kazy.53640 Malformed Client Hello SSL 3.0 (Session_Id length greater than Client_Hello Length)"),
        ("1:2802895", "ETPRO POLICY Suspicious user agent(Industry Update Control)"),
        ("1:2804116", "ETPRO MALWARE User-Agent (MRSPUTNIK)"),
        ("1:2013031", "ET POLICY Python-urllib/ Suspicious User Agent"),
        ("1:2803564", "ETPRO WORM Worm.Win32.Morto.A Propagating via Windows Remote Desktop Protocol"),
        ("1:2012936", "ET SCAN ZmEu Scanner User-Agent Inbound"),
        ("1:2011699", "ET P2P Bittorrent P2P Client User-Agent (Transmission/1.x)"),
        ("1:2804530", "ETPRO TROJAN P2P-Worm.Win32.Palevo.cgrr P2P traffic"),
        ("1:2461", "GPL CHAT Yahoo IM conference watch"),
        ("1:2014726", "ET POLICY Outdated Windows Flash Version IE"),
        ("1:2014169", "ET POLICY DNS Query for .su TLD (Soviet Union) Often Malware Related"),
        ("1:1201", "GPL WEB_SERVER 403 Forbidden"),
        ("1:2011712", "ET P2P Bittorrent P2P Client User-Agent (FDM 3.x)"),
        ("1:2803090", "ETPRO TROJAN Win32.Chebri.A Checkin"),
        ("1:2013451", "ET TROJAN NgrBot IRC CnC Channel Join"),
        ("1:100000230", "GPL CHAT MISC Jabber/Google Talk Outgoing Traffic"),
        ("1:2011706", "ET P2P Bittorrent P2P Client User-Agent (uTorrent)"),
        ("1:2102180", "GPL P2P BitTorrent announce request"),
        ("1:2803311", "ETPRO TROJAN Likely Bot Nick in Off Port IRC"),
        ("1:2000345", "ET TROJAN IRC Nick change on non-standard port"),
        ("1:2102458", "GPL CHAT Yahoo IM successful chat join"),
        ("1:2009766", "ET MALWARE IE Toolbar User-Agent (IEToolbar)"),
        ("1:2012811", "ET CURRENT_EVENTS DNS Query to a .tk domain - Likely Hostile"),
        ("1:2013075", "ET CURRENT_EVENTS Large DNS Query possible covert channel"),
        ("1:2012647", "ET POLICY Dropbox.com Offsite File Backup in Use"),
        ("1:2012810", "ET CURRENT_EVENTS HTTP Request to a *.tk domain"),
        ("1:2012247", "ET P2P BTWebClient UA uTorrent in use"),
        ("1:2009715", "ET WEB_SERVER Onmouseover= in URI - Likely Cross Site Scripting Attempt"),
        ("1:2002157", "ET POLICY Skype User-Agent detected"),
        ("1:100000236", "GPL CHAT Jabber/Google Talk Incoming Message"),
        ("1:2011409", "ET DNS DNS Query for Suspicious .co.cc Domain"),
        ("1:2009525", "ET TROJAN Sality - Fake Opera User-Agent"),
        ("1:2008350", "ET POLICY Autoit Windows Automation tool User-Agent in HTTP Request - Possibly Hostile"),
        ("1:2012606", "ET SCAN Havij SQL Injection Tool User-Agent Inbound"),
        ("1:2009005", "ET MALWARE Simbar Spyware User-Agent Detected"),
        ("1:2012327", "ET MALWARE All Numerical .cn Domain Likely Malware Related"),
        ("1:2009714", "ET WEB_SERVER Script tag in URI, Possible Cross Site Scripting Attempt"),
        ("1:2011582", "ET POLICY Vulnerable Java Version 1.6.x Detected"),
        ("1:2015015", "ET POLICY Download Request to Hotfile.com"),
        ("1:100000235", "GPL CHAT Jabber/Google Talk Logon Success"),
        ("1:2102181", "GPL P2P BitTorrent transfer"),
        ("1:2002911", "ET SCAN Potential VNC Scan 5900-5920"),
        ("1:2007771", "ET TROJAN Pushdo Update URL Detected"),
        ("1:2002087", "ET POLICY Inbound Frequent Emails - Possible Spambot Inbound"),
        ("1:2012887", "ET POLICY Http Client Body contains pass= in cleartext"),
        ("1:2002334", "ET CHAT Google IM traffic Jabber client sign-on"),
        ("1:2009995", "ET MALWARE User-Agent (ONANDON)"),
        ("1:100000232", "GPL CHAT Google Talk Logon"),
        ("1:2009702", "ET POLICY DNS Update From External net"),
        ("1:2012204", "ET SCAN Modified Sipvicious Sundayddr Scanner (sipsscuser)"),
        ("1:2011766", "ET SCAN Modified Sipvicious User-Agent Detected (sundayddr)"),
        ("1:2009971", "ET P2P eMule KAD Network Hello Request (2)"),
        ("1:2003310", "ET P2P Edonkey Publicize File"),
        ("1:2006380", "ET POLICY Outgoing Basic Auth Base64 HTTP Password detected unencrypted"),
        ("1:2804097", "ETPRO TROJAN Win32/Kryptik.WPE User-Agent (YZF)"),
        ("1:2003317", "ET P2P Edonkey Search Request (any type file)"),
        ("1:2801348", "ETPRO TROJAN Mariposa or Palevo Bot Response from Server"),
        ("1:2009930", "ET MALWARE User-Agent (User Agent) - Likely Hostile"),
        ("1:2013715", "ET POLICY BingBar ToolBar User-Agent (BingBar)"),
        ("1:2010935", "ET POLICY Suspicious inbound to MSSQL port 1433"),
        ("1:2008581", "ET P2P BitTorrent DHT ping request"),
        ("1:2008578", "ET SCAN Sipvicious Scan"),
        ("1:1418", "GPL SNMP request tcp"),
        ("1:2803961", "ETPRO MALWARE Adware.Win32/GameVance User-Agent (tl_v)"),
        ("1:2002910", "ET SCAN Potential VNC Scan 5800-5820"),
        ("1:2803880", "ETPRO TROJAN Win32/Sality.AT Checkin"),
        ("1:2452", "GPL CHAT Yahoo IM ping"),
        ("1:2003320", "ET P2P Edonkey Search Results"),
        ("1:100000876", "GPL CHAT Google Talk Version Check"),
        ("1:2804724", "ETPRO TROJAN Virus.Win32.Virut.ce Checkin"),
        ("1:2003313", "ET P2P Edonkey Connect Reply and Server List"),
        ("1:2002166", "ET MALWARE Alexa Search Toolbar User-Agent (Alexa Toolbar)"),
        ("1:2009358", "ET SCAN Nmap Scripting Engine User-Agent Detected (Nmap Scripting Engine)"),
        ("1:2010936", "ET POLICY Suspicious inbound to Oracle SQL port 1521"),
        ("1:2003315", "ET P2P Edonkey Search Reply"),
        ("1:2003068", "ET SCAN Potential SSH Scan OUTBOUND"),
        ("1:2101616", "GPL DNS named version attempt"),
        ("1:2001258", "ET CHAT Yahoo IM conference message"),
        ("1:2001595", "ET POLICY Skype VOIP Checking Version (Startup)"),
        ("1:2013028", "ET POLICY curl User-Agent Outbound"),
        ("1:2001972", "ET SCAN Behavioral Unusually fast Terminal Server Traffic, Potential Scan or Infection"),
        ("1:2804619", "ETPRO POLICY Request to Externally Hosted proxy config file .pac"),
        ("1:2007695", "ET POLICY Windows 98 User-Agent Detected - Possible Malware or Non-Updated System"),
        ("1:2011124", "ET MALWARE Suspicious FTP 220 Banner on Local Port (spaced)"),
        ("1:2001034", "ET MALWARE Fun Web Products Agent Traffic"),
        ("1:2804732", "ETPRO POLICY Software Informer access"),
        ("1:2102466", "GPL NETBIOS SMB-DS IPC$ unicode share access"),
        ("1:2010493", "ET SCAN Non-Allowed Host Tried to Connect to MySQL Server"),
        ("1:2012612", "ET TROJAN Hiloti Style GET to PHP with invalid terse MSIE headers"),
        ("1:2100538", "GPL NETBIOS SMB IPC$ unicode share access"),
        ("1:2012982", "ET SMTP Abuseat.org Block Message"),
        ("1:2008189", "ET TROJAN SpamTool.Win32.Agent.gy/Grum/Tedroo Or Similar HTTP Checkin"),
        ("1:2003089", "ET GAMES STEAM Connection (v2)"),
        ("1:2003219", "ET MALWARE Alexa Spyware Reporting"),
        ("1:2800668", "ETPRO NETBIOS Samba receive_smb_raw SMB Packets Parsing Buffer Overflow"),
        ("1:2010885", "ET TROJAN BlackEnergy v2.x HTTP Request with Encrypted Variables"),
        ("1:2008115", "ET POLICY Tor Get Status Request"),
        ("1:2007854", "ET MALWARE User-Agent (Mozilla) - Possible Spyware Related"),
        ("1:2012889", "ET POLICY Http Client Body contains pw= in cleartext"),
        ("1:2003616", "ET WEB_SERVER DataCha0s Web Scanner/Robot"),
        ("1:100000892", "GPL VOIP Q.931 Invalid Call Reference Length Buffer Overflow"),
        ("1:2012843", "ET POLICY Cleartext WordPress Login"),
        ("1:2006435", "ET SCAN LibSSH Based SSH Connection - Often used as a BruteForce Tool"),
        ("1:2003924", "ET SCAN WebHack Control Center User-Agent Inbound (WHCC/)"),
        ("1:2014384", "ET DOS Microsoft Remote Desktop (RDP) Syn then Reset 30 Second DoS Attempt"),
        ("1:2002117", "ET GAMES Battle.net connection reset (possible IP-Ban)"),
        ("1:2006546", "ET SCAN LibSSH Based Frequent SSH Connections Likely BruteForce Attack!"),
        ("1:2002878", "ET POLICY iTunes User Agent"),
        ("1:2002026", "ET CHAT IRC PRIVMSG command"),
        ("1:2011821", "ET CURRENT_EVENTS User-Agent used in known DDoS Attacks Detected outbound"),
        ("1:2001855", "ET MALWARE Fun Web Products Spyware User-Agent (FunWebProducts)"),
        ("1:2008985", "ET POLICY Internal Host Retrieving External IP via whatismyip.com Automation Page - Possible Infection"),
        ("1:2101948", "GPL DNS zone transfer UDP"),
        ("1:2013926", "ET POLICY HTTP traffic on port 443 (POST)"),
        ("1:2009153", "ET WEB_SERVER PHP Generic Remote File Include Attempt (FTP)"),
        ("1:2014304", "ET POLICY External IP Lookup Attempt To Wipmania"),
        ("1:2014170", "ET POLICY HTTP Request to .su TLD (Soviet Union) Often Malware Related"),
        ("1:2014846", "ET CURRENT_EVENTS Wordpress timthumb look-alike domain list RFI"),
        ("1:2010939", "ET POLICY Suspicious inbound to PostgreSQL port 5432"),
        ("1:2008986", "ET POLICY Internal Host Retrieving External IP via whatismyip.com - Possible Infection"),
        ("1:2802104", "ETPRO POLICY MOBILE iPhone securityd User-Agent Detected"),
        ("1:2013053", "ET WEB_SERVER PyCurl Suspicious User Agent Inbound"),
        ("1:2009699", "ET VOIP REGISTER Message Flood UDP"),
        ("1:2009099", "ET P2P ThunderNetwork UDP Traffic"),
        ("1:2803780", "ETPRO TROJAN Backdoor.Win32.Pefsire.A Checkin 2"),
        ("1:937", "GPL WEB_SERVER _vti_rpc access"),
        ("1:2010494", "ET SCAN Multiple MySQL Login Failures, Possible Brute Force Attempt"),
        ("1:2804713", "ETPRO TROJAN USER-AGENT (MailRuSputnik)"),
        ("1:2011823", "ET CURRENT_EVENTS User-Agent used in known DDoS Attacks Detected outbound 2"),
        ("1:2003466", "ET WEB_SERVER PHP Attack Tool Morfeus F Scanner"),
        ("1:2009970", "ET P2P eMule Kademlia Hello Request"),
        ("1:2007880", "ET MALWARE User-Agent (single dash)"),
        ("1:2002997", "ET WEB_SERVER PHP Remote File Inclusion (monster list http)"),
        ("1:2000369", "ET P2P BitTorrent Announce"),
        ("1:2011540", "ET POLICY OpenSSL Demo CA - Internet Widgits Pty (O)"),
        ("1:2013057", "ET WEB_SERVER Inbound PHP User-Agent"),
        ("1:2664", "GPL IMAP login format string attempt"),
        ("1:2008085", "ET MALWARE Alexa Search Toolbar User-Agent 2 (Alexa Toolbar)"),
        ("1:2012078", "ET POLICY Windows-Based OpenSSL Tunnel Outbound"),
        ("1:2007799", "ET P2P Azureus P2P Client User-Agent"),
        ("1:2006402", "ET POLICY Incoming Basic Auth Base64 HTTP Password detected unencrypted"),
        ("1:2011517", "ET MALWARE Inbound AlphaServer User-Agent (Powered By 64-Bit Alpha Processor)"),
        ("1:2001263", "ET CHAT Yahoo IM conference request"),
        ("1:2006446", "ET WEB_SERVER Possible SQL Injection Attempt UNION SELECT"),
        ("1:2001259", "ET CHAT Yahoo IM file transfer request"),
        ("1:2003195", "ET POLICY Unusual number of DNS No Such Name Responses"),
        ("1:2012522", "ET POLICY DNS Query For XXX Adult Site Top Level Domain"),
        ("1:2460", "GPL CHAT Yahoo IM conference request"),
        ("1:2014702", "ET DNS Non-DNS or Non-Compliant DNS traffic on DNS port Opcode 8 through 15 set"),
        ("1:2802106", "ETPRO POLICY MOBILE iPhone iTunes User-Agent Detected"),
        ("1:2012141", "ET POLICY Protocol 41 IPv6 encapsulation potential 6in4 IPv6 tunnel active"),
        ("1:2010904", "ET MALWARE Fake Mozilla User-Agent (Mozilla/0.xx) Inbound"),
        ("1:2012888", "ET POLICY Http Client Body contains pwd= in cleartext"),
        ("1:2012709", "ET POLICY MS Remote Desktop Administrator Login Request"),
        ("1:2011144", "ET WEB_SERVER PHP Easteregg Information-Disclosure (funny-logo)"),
        ("1:2011141", "ET WEB_SERVER PHP Easteregg Information-Disclosure (phpinfo)"),
        ("1:2012328", "ET MALWARE All Numerical .ru Domain Lookup Likely Malware Related"),
        ("1:2801157", "ETPRO SCADA SCHWEITZER (Event 15) Station Number Error"),
        ("1:2002027", "ET CHAT IRC PING command"),
        ("1:2014703", "ET DNS Non-DNS or Non-Compliant DNS traffic on DNS port Reserved Bit Set"),
        ("1:2007929", "ET MALWARE User-Agent (User-Agent Mozilla/4.0 (compatible ))"),
        ("1:2014371", "ET CURRENT_EVENTS Possible Kelihos .eu CnC Domain Generation Algorithm (DGA) Lookup Detected"),
        ("1:2009376", "ET CHAT MSN User-Agent Activity"),
        ("1:2009375", "ET CHAT General MSN Chat Activity"),
        ("1:2002992", "ET SCAN Rapid POP3 Connections - Possible Brute Force Attack"),
        ("1:2924", "GPL NETBIOS SMB-DS repeated logon failure"),
        ("1:2012312", "ET TROJAN Generic Trojan with /? and Indy Library User-Agent"),
        ("1:2009967", "ET P2P eMule KAD Network Connection Request"),
        ("1:2455", "GPL CHAT Yahoo IM conference message"),
        ("1:2008583", "ET P2P BitTorrent DHT nodes reply"),
        ("1:2014701", "ET DNS Non-DNS or Non-Compliant DNS traffic on DNS port Opcode 6 or 7 set"),
        ("1:2002945", "ET POLICY Java Url Lib User Agent Web Crawl"),
        ("1:2013659", "ET POLICY Self Signed SSL Certificate (SomeOrganizationalUnit)"),
        ("1:2008052", "ET MALWARE User-Agent (Internet Explorer)"),
        ("1:2008585", "ET P2P BitTorrent DHT announce_peers request"),
        ("1:2010794", "ET WEB_SERVER DFind w00tw00t GET-Requests"),
        ("1:2010908", "ET MALWARE Mozilla User-Agent (Mozilla/5.0) Inbound Likely Fake"),
        ("1:2803889", "ETPRO MALWARE Adware/Win32.MediaGet User-Agent (mediaget)"),
        ("1:2013407", "ET POLICY SSL MiTM Vulnerable or EOL iOS 4.x device"),
        ("1:2013710", "ET POLICY FreeRide Games Some AVs report as TrojWare.Win32.Trojan.Agent.Gen"),
        ("1:2802103", "ETPRO POLICY MOBILE iPhone locationd User-Agent Detected"),
        ("1:2010768", "ET SCAN Open-Proxy ScannerBot (webcollage-UA) "),
        ("1:2001240", "ET POLICY Cisco Device New Config Built"),
        ("1:2100566", "GPL POLICY PCAnywhere server response"),
        ("1:2100474", "GPL SCAN superscan echo"),
        ("1:2802102", "ETPRO POLICY MOBILE iPhone locationd update to Apple"),
        ("1:2101129", "GPL WEB_SERVER .htaccess access"),
        ("1:2006445", "ET WEB_SERVER Possible SQL Injection Attempt SELECT FROM"),
        ("1:2010819", "ET CHAT Facebook Chat using XMPP"),
        ("1:2803167", "ETPRO POLICY MOBILE Android Device User-Agent"),
        ("1:2804756", "ETPRO TROJAN pandora-ddos-bot User-Agent (Mozilla/100)"),
        ("1:2002400", "ET USER_AGENTS Suspicious User Agent (Microsoft Internet Explorer)"),
        ("1:2001996", "ET MALWARE UCMore Spyware User-Agent (EI)"),
        ("1:2002167", "ET POLICY Software Install Reporting via HTTP - Wise User Agent (Wise) Sometimes Malware Related"),
        ("1:2802841", "ETPRO USER_AGENTS Suspicious User-Agent Setup Agent - Likely Malware"),
        ("1:2803264", "ETPRO TROJAN DMSpammer/Nedsym Checkin"),
        ("1:2001262", "ET CHAT Yahoo IM conference offer invitation"),
        ("1:2011227", "ET POLICY User-Agent (NSIS_Inetc (Mozilla)) - Sometimes used by hostile installers"),
        ("1:100000877", "GPL CHAT Google Talk Startup"),
        ("1:2013851", "ET DNS Query for Suspicious .us.tf Domain"),
        ("1:2007826", "ET TROJAN Suspicious Useragent Used by Several trojans (API-Guide test program)"),
        ("1:2001858", "ET MALWARE Hotbar Spyware User-Agent (Hotbar)"),
        ("1:2013784", "ET POLICY Windows Mobile 7.0 User-Agent detected"),
        ("1:2010143", "ET P2P Vuze BT UDP Connection (4)"),
        ("1:2009968", "ET P2P eMule KAD Network Connection Request(2)"),
        ("1:2009020", "ET POLICY Internal Host Retrieving External IP via ipchicken.com - Possible Infection"),
        ("1:2001682", "ET CHAT MSN IM Poll via HTTP"),
        ("1:2102465", "GPL NETBIOS SMB-DS IPC$ share access"),
        ("1:2012983", "ET SMTP Spamcop.net Block Message"),
        ("1:2012000", "ET MALWARE ASKTOOLBAR.DLL Reporting"),
        ("1:2003496", "ET MALWARE AskSearch Toolbar Spyware User-Agent (AskBar)"),
        ("1:2804286", "ETPRO POLICY User-Agent (InstallChecker)"),
        ("1:2014137", "ET MALWARE Common Adware Library ISX User Agent Detected"),
        ("1:2001581", "ET SCAN Behavioral Unusual Port 135 traffic, Potential Scan or Infection"),
        ("1:2012648", "ET POLICY Dropbox Client Broadcasting"),
        ("1:2014297", "ET POLICY Vulnerable Java Version 1.7.x Detected"),
        ("1:2008124", "ET TROJAN Likely Bot Nick in IRC (USA +..)"),
        ("1:2015023", "ET WEB_SERVER IIS 8.3 Filename With Wildcard (Possible File/Dir Bruteforce)"),
        ("1:2012985", "ET SMTP Sorbs.net Block Message"),
        ("1:2010442", "ET TROJAN Possible Storm Variant HTTP Post (U)"),
        ("1:2800833", "ETPRO SMTP IBM Lotus Domino nrouter.exe iCalendar MAILTO Stack Buffer Overflow"),
        ("1:2459", "GPL CHAT Yahoo IM conference offer invitation"),
        ("1:2001564", "ET MALWARE MarketScore.com Spyware Proxied Traffic"),
        ("1:2804233", "ETPRO POLICY dl.dropbox Download"),
        ("1:2008597", "ET SCAN Cisco Torch SNMP Scan"),
        ("1:2014123", "ET POLICY Softango.com Installer Checking For Update"),
        ("1:2456", "GPL CHAT Yahoo Messenger File Transfer Receive Request"),
        ("1:2010963", "ET WEB_SERVER SELECT USER SQL Injection Attempt in URI"),
        ("1:100000197", "GPL ICMP undefined code"),
        ("1:100000186", "GPL WEB_SERVER WEB-PHP phpinfo access"),
        ("1:1420", "GPL SNMP trap tcp"),
        ("1:2012886", "ET POLICY Http Client Body contains passwd= in cleartext"),
        ("1:2012079", "ET POLICY Windows-Based OpenSSL Tunnel Connection Outbound 2"),
        ("1:2008488", "ET TROJAN Suspicious User-Agent (NULL)"),
        ("1:2003626", "ET MALWARE Double User-Agent (User-Agent User-Agent)"),
        ("1:2011710", "ET P2P Bittorrent P2P Client User-Agent (BitComet)"),
        ("1:2003319", "ET P2P Edonkey Search Request (search by name)"),
        ("1:2100257", "GPL DNS named version attempt"),
        ("1:2001804", "ET POLICY ICQ Login"),
        ("1:2001562", "ET MALWARE MarketScore.com Spyware User Configuration and Setup Access User-Agent (OSSProxy)"),
        ("1:2001865", "ET MALWARE MyWebSearch Spyware User-Agent (MyWebSearch)"),
        ("1:2013888", "ET POLICY Cnet App Download and Checkin"),
        ("1:2012849", "ET MOBILE_MALWARE Possible Mobile Malware POST of IMSI International Mobile Subscriber Identity in URI"),
        ("1:2011410", "ET DNS DNS Query for Suspicious .cz.cc Domain"),
        ("1:2009867", "ET TROJAN Suspicious User-Agent (Mozilla/3.0 (compatible))"),
        ("1:2003492", "ET MALWARE Suspicious Mozilla User-Agent - Likely Fake (Mozilla/4.0)"),
        ("1:2002994", "ET SCAN Rapid IMAP Connections - Possible Brute Force Attack"),
        ("1:2014122", "ET MALWARE W32/OpenCandy Adware Checkin"),
        ("1:2001239", "ET POLICY Cisco Device in Config Mode"),
        ("1:2010441", "ET TROJAN Possible Storm Variant HTTP Post (S)"),
        ("1:2009362", "ET WEB_SERVER /system32/ in Uri - Possible Protected Directory Access Attempt"),
        ("1:2009361", "ET WEB_SERVER cmd.exe In URI - Possible Command Execution Attempt"),
        ("1:2008312", "ET SCAN DEBUG Method Request with Command"),
        ("1:2003636", "ET MALWARE Sality Virus User Agent Detected (KUKU)"),
        ("1:2003410", "ET POLICY FTP Login Successful"),
        ("1:2803697", "ETPRO TROJAN Backdoor.Win32.Protux.B Checkin 1"),
        ("1:2002839", "ET MALWARE My Search Spyware Config Download"),
        ("1:2002158", "ET WEB_SERVER XML-RPC for PHP Remote Code Injection"),
        ("1:2001256", "ET CHAT Yahoo IM conference invitation"),
        ("1:2014728", "ET TROJAN Smoke Loader Checkin r=gate"),
        ("1:2804830", "ETPRO TROJAN Win32.Sality.bh Checkin 2"),
        ("1:2102003", "GPL SQL Slammer Worm propagation attempt"),
        ("1:2014047", "ET TROJAN Double HTTP/1.1 Header Inbound - Likely Hostile Traffic"),
        ("1:2012734", "ET USER_AGENTS Suspicious User-Agent String (AskPartnerCobranding)"),
        ("1:2003493", "ET MALWARE AskSearch Spyware User-Agent (AskSearchAssistant)"),
        ("1:2001257", "ET CHAT Yahoo IM conference logon success"),
        ("1:2101867", "GPL RPC xdmcp info query"),
        ("1:2014828", "ET CURRENT_EVENTS UPS Spam Inbound"),
        ("1:2013293", "ET TROJAN Win32/Glupteba CnC Checkin"),
        ("1:2011225", "ET POLICY Suspicious User Agent (AskInstallChecker)"),
        ("1:2009698", "ET VOIP INVITE Message Flood UDP"),
        ("1:2003469", "ET POLICY AOL Toolbar User-Agent (AOLToolbar)"),
        ("1:2003262", "ET MALWARE SOCKSv4 HTTP Proxy Inbound Request (Windows Source)"),
        ("1:2002993", "ET SCAN Rapid POP3S Connections - Possible Brute Force Attack"),
        ("1:1251", "GPL TELNET Bad Login"),
        ("1:100000158", "GPL VOIP SIP INVITE message flooding"),
        ("1:2804625", "ETPRO TROJAN Trojan/Win32.Vaklik.gen Checkin"),
        ("1:884", "GPL EXPLOIT formmail access"),
        ("1:660", "GPL SMTP expn root"),
        ("1:2014919", "ET POLICY Microsoft Online Storage Client Hello TLSv1 Possible SkyDrive (1)"),
        ("1:2013792", "ET SCAN Apache mod_proxy Reverse Proxy Exposure 2"),
        ("1:2013791", "ET SCAN Apache mod_proxy Reverse Proxy Exposure 1"),
        ("1:2013036", "ET TROJAN Java EXE Download by Vulnerable Version - Likely Driveby"),
        ("1:2012298", "ET MALWARE User-Agent (0xa10xa1HttpClient)"),
        ("1:2012296", "ET VOIP Modified Sipvicious Asterisk PBX User-Agent"),
        ("1:2008216", "ET TROJAN Suspicious User-Agent (NSIS_DOWNLOAD)"),
        ("1:2002995", "ET SCAN Rapid IMAPS Connections - Possible Brute Force Attack"),
        ("1:1446", "GPL SMTP vrfy root"),
        ("1:1016", "GPL WEB_SERVER global.asa access"),
        ("1:2013290", "ET POLICY MOBILE Apple device leaking UDID from SpringBoard via GET"),
        ("1:2800554", "ETPRO DOS Microsoft Windows SMTP Service MX Record Denial Of Service"),
        ("1:2002659", "ET CHAT Yahoo IM Client Install"),
        ("1:2003286", "ET MALWARE SOCKSv5 UDP Proxy Inbound Connect Request (Windows Source)"),
        ("1:2002844", "ET WEB_SERVER WebDAV search overflow"),
        ("1:2800946", "ETPRO USER_AGENTS Suspicious User-Agent Malware related Windows wget"),
        ("1:2014920", "ET POLICY Microsoft Online Storage Client Hello TLSv1 Possible SkyDrive (2)"),
        ("1:2014374", "ET CURRENT_EVENTS Possible Zeus .info CnC Domain Generation Algorithm (DGA) Lookup NXDOMAIN Response"),
        ("1:2013178", "ET TROJAN Long Fake wget 3.0 User-Agent Detected"),
        ("1:2011768", "ET WEB_SERVER PHP tags in HTTP POST"),
        ("1:2011042", "ET WEB_SERVER MYSQL SELECT CONCAT SQL Injection Attempt"),
        ("1:2010973", "ET TROJAN Vobfus/Changeup/Chinky Download Command"),
        ("1:2009801", "ET POLICY Carbonite.com Backup Software User-Agent (Carbonite Installer)"),
        ("1:2008428", "ET TROJAN Suspicious User-Agent (HTTP Downloader)"),
        ("1:2002025", "ET CHAT IRC JOIN command"),
        ("1:100000429", "GPL WEB_SERVER WEB-MISC JBoss web-console access"),
        ("1:2008113", "ET POLICY Tor Get Server Request"),
        ("1:2011800", "ET POLICY Abnormal User-Agent No space after colon - Likely Hostile"),
        ("1:2010524", "ET WEB_SERVER Possible HTTP 500 XSS Attempt (Internal Source)"),
        ("1:2101945", "GPL WEB_SERVER unicode directory traversal attempt"),
        ("1:2100537", "GPL NETBIOS SMB IPC$ share access"),
        ("1:2100476", "GPL SCAN webtrends scanner"),
        ("1:2014296", "ET WEB_SERVER eval/base64_decode Exploit Attempt Inbound"),
        ("1:2013406", "ET POLICY SSL MiTM Vulnerable or EOL iOS 3.x device"),
        ("1:2013224", "ET POLICY Suspicious User-Agent Containing .exe"),
        ("1:2011802", "ET DNS DNS Lookup for localhost.DOMAIN.TLD"),
        ("1:2011374", "ET CURRENT_EVENTS HTTP Request to a *.co.cc domain"),
        ("1:2010786", "ET CHAT Facebook Chat (settings)"),
        ("1:2010766", "ET POLICY Proxy TRACE Request - inbound"),
        ("1:2010644", "ET CURRENT_EVENTS UPS Spam Inbound"),
        ("1:2009972", "ET P2P eMule KAD Network Server Status Request"),
        ("1:2008570", "ET POLICY External Unencrypted Connection to BASE Console"),
        ("1:2007727", "ET P2P possible torrent download"),
        ("1:2002383", "ET SCAN Potential FTP Brute-Force attempt"),
        ("1:2001492", "ET MALWARE ISearchTech.com XXXPornToolbar Activity (MyApp)"),
        ("1:2001059", "ET P2P Ares traffic"),
        ("1:2453", "GPL CHAT Yahoo IM conference invitation"),
        ("1:2002327", "ET CHAT Google Talk (Jabber) Client Login"),
        ("1:2454", "GPL CHAT Yahoo IM conference logon success"),
        ("1:2012956", "ET DNS DNS Query for a Suspicious *.co.tv domain"),
        ("1:951", "GPL WEB_SERVER authors.pwd access"),
        ("1:2923", "GPL NETBIOS SMB repeated logon failure"),
        ("1:2803073", "ETPRO WEB_SERVER Oracle Web Server Expect Header Cross-Site Scripting"),
        ("1:2801424", "ETPRO MALWARE Adware.Win32.OpenCandy Checkin 1"),
        ("1:2014827", "ET CURRENT_EVENTS FedEX Spam Inbound"),
        ("1:2014631", "ET CURRENT_EVENTS FakeAV Security Shield payment page request"),
        ("1:2014545", "ET CURRENT_EVENTS TDS Sutra - page redirecting to a SutraTDS"),
        ("1:2013315", "ET TROJAN Suspicious User-Agent (Agent and 5 or 6 digits)"),
        ("1:2013172", "ET DNS DNS Query for a Suspicious *.cu.cc domain"),
        ("1:2012492", "ET CURRENT_EVENTS DHL Spam Inbound"),
        ("1:2011736", "ET GAMES TeamSpeak2 Connection/Ping"),
        ("1:2010148", "ET CURRENT_EVENTS DHL Spam Inbound"),
        ("1:2010142", "ET P2P Vuze BT UDP Connection (3)"),
        ("1:2006443", "ET WEB_SERVER Possible SQL Injection Attempt DELETE FROM"),
        ("1:2003337", "ET MALWARE Suspicious User Agent (Autoupdate)"),
        ("1:2003055", "ET MALWARE Suspicious FTP 220 Banner on Local Port (-)"),
        ("1:2002935", "ET POLICY Possible Web Crawl - libwww-perl User Agent"),
        ("1:2002111", "ET GAMES Battle.net invalid cdkey"),
        ("1:2002108", "ET GAMES Battle.net Warcraft 3 The Frozen throne login"),
        ("1:2001298", "ET P2P eDonkey Server Status Request"),
        ("1:2000378", "ET EXPLOIT MS-SQL DOS attempt (08)"),
        ("1:2803034", "ETPRO TROJAN W32/Virut.n.gen Checkin"),
        ("1:2803009", "ETPRO USER_AGENTS Suspicious User-Agent (MyLove)"),
        ("1:2801301", "ETPRO USER_AGENTS Select Rebates Spyware UA Detected"),
        ("1:2800705", "ETPRO EXPLOIT Microsoft Outlook iCal Meeting Request Malformed VEVENT Record Dereference Memory Corruption"),
        ("1:2101877", "GPL WEB_SERVER printenv access"),
        ("1:2014756", "ET POLICY Logmein.com SSL Remote Control Access"),
        ("1:2014734", "ET POLICY BitTorrent - Torrent File Downloaded"),
        ("1:2014124", "ET POLICY Softango.com Installer POSTing Data"),
        ("1:2013933", "ET POLICY HTTP traffic on port 443 (CONNECT)"),
        ("1:2013847", "ET DNS Query for Suspicious .net.tf Domain"),
        ("1:2013795", "ET TROJAN Bifrose/Cycbot Checkin"),
        ("1:2013703", "ET CURRENT_EVENTS Suspicious Self Signed SSL Certificate to 'My Company Ltd' could be SSL C&C"),
        ("1:2013485", "ET CURRENT_EVENTS Phoenix Java MIDI Exploit Received"),
        ("1:2013484", "ET CURRENT_EVENTS Phoenix Java MIDI Exploit Received By Vulnerable Client"),
        ("1:2013438", "ET CURRENT_EVENTS HTTP Request to a *.uni.cc domain"),
        ("1:2013360", "ET CURRENT_EVENTS Wordpress possible Malicious DNS-Requests - photobucket.com.* "),
        ("1:2013332", "ET TROJAN FakeAV Landing Page"),
        ("1:2013181", "ET CURRENT_EVENTS Ponmocup Redirection from infected Website to Trojan-Downloader"),
        ("1:2012955", "ET CURRENT_EVENTS HTTP Request to a *.co.tv domain"),
        ("1:2012711", "ET POLICY MS Remote Desktop POS User Login Request"),
        ("1:2012710", "ET POLICY MS Terminal Server Root login"),
        ("1:2010938", "ET POLICY Suspicious inbound to mSQL port 4333"),
        ("1:2009969", "ET P2P eMule KAD Network Firewalled Request"),
        ("1:2008015", "ET MALWARE User-Agent (Win95)"),
        ("1:2003927", "ET TROJAN Suspicious User-Agent (HTTPTEST) - Seen used by downloaders"),
        ("1:2003316", "ET P2P Edonkey IP Query End"),
        ("1:2003311", "ET P2P Edonkey Publicize File ACK"),
        ("1:2003287", "ET MALWARE SOCKSv5 UDP Proxy Inbound Connect Request (Linux Source)"),
        ("1:2002842", "ET SCAN MYSQL 4.1 brute force root login attempt"),
        ("1:2002801", "ET POLICY Google Desktop User-Agent Detected"),
        ("1:2002402", "ET MALWARE Spyware Related User-Agent (UtilMind HTTPGet)"),
        ("1:2002024", "ET CHAT IRC NICK command"),
        ("1:2000340", "ET P2P Kaaza Media desktop p2pnetworking.exe Activity"),
        ("1:1071", "GPL WEB_SERVER .htpasswd access"),
        ("1:2013289", "ET POLICY MOBILE Apple device leaking UDID from SpringBoard"),
        ("1:977", "GPL EXPLOIT .cnf access"),
        ("1:958", "GPL WEB_SERVER service.cnf access"),
        ("1:598", "GPL RPC portmap listing TCP 111"),
        ("1:2804980", "ETPRO MALWARE Zugo Adware GeoIP Check"),
        ("1:2804972", "ETPRO TROJAN Herpbot.B ICMP"),
        ("1:2804834", "ETPRO MALWARE Installmate Installer Checkin"),
        ("1:2803106", "ETPRO DNS ISC BIND RRSIG RRsets Denial of Service TCP 1"),
        ("1:2802954", "ETPRO MALWARE Zugo Adware Installer Checkin"),
        ("1:2801632", "ETPRO SMTP Multiple Products STARTTLS Plaintext Command Injection"),
        ("1:2800021", "ETPRO EXPLOIT Squid WCCP Message Receive Buffer Overflow"),
        ("1:2102470", "GPL NETBIOS SMB C$ unicode share access"),
        ("1:2101874", "GPL WEB_SERVER Oracle Java Process Manager access"),
        ("1:2101145", "GPL WEB_SERVER /~root access"),
        ("1:2100494", "GPL ATTACK_RESPONSE command completed"),
        ("1:2014939", "ET POLICY DNS Query for TOR Hidden Domain .onion Accessible Via TOR"),
        ("1:2014893", "ET SCAN critical.io Scan"),
        ("1:2014291", "ET TROJAN W32/Backdoor.Kbot Config Retrieval"),
        ("1:2013974", "ET POLICY Suspicious Invalid HTTP Accept Header of ?"),
        ("1:2013857", "ET DNS Query for Suspicious .de.tf Domain"),
        ("1:2013479", "ET SCAN Behavioral Unusually fast Terminal Server Traffic, Potential Scan or Infection"),
        ("1:2013236", "ET TROJAN Palevo (OUTBOUND)"),
        ("1:2011143", "ET WEB_SERVER PHP Easteregg Information-Disclosure (zend-logo)"),
        ("1:2011142", "ET WEB_SERVER PHP Easteregg Information-Disclosure (php-logo)"),
        ("1:2009152", "ET WEB_SERVER PHP Generic Remote File Include Attempt (HTTPS)"),
        ("1:2008974", "ET MALWARE User-Agent (Mozilla/4.0 (compatible))"),
        ("1:2008411", "ET TROJAN LDPinch SMTP Password Report with mail client The Bat!"),
        ("1:2008038", "ET MALWARE User-Agent (Mozilla/4.0 (compatible ICS))"),
        ("1:2003263", "ET MALWARE SOCKSv4 HTTP Proxy Inbound Request (Linux Source)"),
        ("1:2002926", "ET SNMP Cisco Non-Trap PDU request on SNMPv1 random port"),
        ("1:2002825", "ET POLICY POSSIBLE Web Crawl using Curl"),
        ("1:2002685", "ET WEB_SERVER Barracuda Spam Firewall img.pl Remote Directory Traversal Attempt"),
        ("1:2001872", "ET MALWARE Visicom Spyware User-Agent (Visicom)"),
        ("1:2001223", "ET MALWARE Regnow.com Access"),
        ("1:1242", "GPL EXPLOIT ISAPI .ida access"),
        ("1:2003608", "ET POLICY Baidu.com Related Agent User-Agent (iexp)"),
        ("1:2012230", "ET WEB_SERVER Likely Malicious Request for /proc/self/environ"),
        ("1:2103070", "GPL IMAP fetch overflow attempt"),
        ("1:2803849", "ETPRO WEB_SERVER Microsoft Forefront Unified Access Gateway XSS Attempt 3"),
        ("1:2013535", "ET CURRENT_EVENTS HTTP Request to a *.tc domain"),
        ("1:2012390", "ET P2P Libtorrent User-Agent"),
        ("1:2010920", "ET WEB_SERVER Exploit Suspected PHP Injection Attack (cmd=)"),
        ("1:2009387", "ET POLICY PPTP Requester is not authorized to establish a command channel"),
    ]
