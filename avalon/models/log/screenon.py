import random

from avalon.models.templates import log_templates, LogTemplateModel


@log_templates(default_keys=True)
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
