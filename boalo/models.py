import os

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class User(Base):

    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    name = Column(String(512))
    username = Column(String(128))
    vpn_username = Column(String(16), nullable=True)
    vpn_password = Column(String(128), nullable=True)
    credit = Column(Float, default=0)
    activated = Column(Boolean, default=False)
    banned = Column(Boolean, default=False)
    locked = Column(Boolean, default=False)

    @property
    def vpn_info(self):
        return (f'username: {self.vpn_username}\n'
                f'password: {self.vpn_password}\n')

    def add_vpn(self):
        os.system((f'echo {self.vpn_password} | '
                   f'ocpasswd {self.vpn_username} -c /etc/ocserv/pass.wd'))

    def change_vpn(self, lock):
        if lock:
            os.system((f'ocpasswd -d {self.vpn_username} -c /etc/ocserv/pass.wd'))
        else:
            self.add_vpn()
        self.locked = lock


class Info(Base):

    __tablename__ = "info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(32))
    text = Column(String(4096))


class Invoice(Base):

    __tablename__ = "invoice"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("user.id"))
    paid = Column(Boolean, default=False)
    fee = Column(Float())
    date = Column(DateTime)
