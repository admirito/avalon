from avalon.models.templates import log_templates, LogTemplateModel
from avalon.models.rand import random_username


@log_templates(default_keys=True)
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


@log_templates(default_keys=True)
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
