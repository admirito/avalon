import datetime
import random

from avalon.models.templates import log_templates, LogTemplateModel


@log_templates(default_keys=True)
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
