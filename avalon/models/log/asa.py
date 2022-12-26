from avalon.models.templates import log_templates, LogTemplateModel


@log_templates(default_keys=True)
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
