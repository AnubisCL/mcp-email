#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Email Service - 使用官方Python SDK实现
功能：
1. 读取最近几封邮件（可传入参数）
2. 发送邮件给指定人（可传入参数）
参数从环境变量读取
"""

import os
import email
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.header
import email.encoders
import email.mime.base
from typing import List, Optional, Dict, Any

from fastmcp import FastMCP
from pydantic import Field, BaseModel


class EmailConfig(BaseModel):
    """邮件配置模型"""
    protocol: str = Field(default=os.getenv('MCP_EMAIL_PROTOCOL', 'imap'))
    imap_server: str = Field(default=os.getenv('MCP_EMAIL_SERVER', 'imap.163.com'))
    imap_port: int = Field(default=int(os.getenv('MCP_EMAIL_PORT', '993')))
    smtp_server: str = Field(default=os.getenv('MCP_SMTP_SERVER', 'smtp.163.com'))
    smtp_port: int = Field(default=int(os.getenv('MCP_SMTP_PORT', '465')))
    username: str = Field(default=os.getenv('MCP_EMAIL_USERNAME', ''))
    password: str = Field(default=os.getenv('MCP_EMAIL_PASSWORD', ''))
    save_path: str = Field(default=os.getenv('MCP_SAVE_PATH', '/Users/anubis/404net/mcp-read-email-py/attachments'))


class EmailMessage(BaseModel):
    """邮件消息模型"""
    date: str
    subject: str
    sender: str
    receiver: str
    content: Optional[str] = None
    content_type: Optional[str] = None
    files: List[str] = Field(default_factory=list)


class ReadEmailsParams(BaseModel):
    """读取邮件参数"""
    count: int = Field(default=1, description="读取邮件数量")
    type: str = Field(default="Unseen", description="邮件类型: All, Unseen, Seen, Recent, Answered, Flagged")
    latest: bool = Field(default=True, description="是否读取最新邮件")


class SendEmailParams(BaseModel):
    """发送邮件参数"""
    to: str = Field(description="收件人邮箱")
    subject: str = Field(description="邮件主题")
    content: str = Field(description="邮件内容")
    content_type: str = Field(default="plain", description="内容类型: plain 或 html")
    attachments: List[str] = Field(default_factory=list, description="附件列表")


class EmailService:
    """邮件服务实现"""
    # 邮件类型
    All, Unseen, Seen, Recent, Answered, Flagged = "All,Unseen,Seen,Recent,Answered,Flagged".split(',')
    
    def __init__(self, config: EmailConfig):
        self.config = config
        # 确保保存路径存在
        if self.config.save_path and not os.path.exists(self.config.save_path):
            os.makedirs(self.config.save_path)
    
    def login_imap(self):
        """登录IMAP服务器"""

        imap_server = imaplib.IMAP4_SSL(self.config.imap_server, self.config.imap_port)
        imap_server.login(self.config.username, self.config.password)
        
        # 解决网易邮箱报错：Unsafe Login
        imaplib.Commands["ID"] = ('AUTH',)
        args = ("name", self.config.username, "contact", self.config.username, "version", "1.0.0", "vendor", "mcpclient")
        imap_server._simple_command("ID", str(args).replace(",", "").replace("'", '"'))
        return imap_server
    
    def login_smtp(self):
        """登录SMTP服务器"""
        smtp_server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port)
        smtp_server.login(self.config.username, self.config.password)
        return smtp_server
    
    @staticmethod
    def format_date(date_str):
        """格式化邮件日期"""
        try:
            # 解析邮件日期
            date_obj = email.utils.parsedate_to_datetime(date_str)
            # 转换为本地时间
            return date_obj.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            return date_str
    
    @staticmethod
    def save_file(file_name, data, save_path=''):
        """保存文件"""
        file_path = os.path.join(save_path, file_name)
        with open(file_path, 'wb') as fp:
            fp.write(data)
        return file_path
    
    def parse_message(self, msg, save_path=''):
        """解析message并下载附件，返回字典类型"""
        message_content, content_type, suffix = None, None, None
        files = []
        
        for part in msg.walk():
            if not part.is_multipart():
                content_type = part.get_content_type()
                filename = part.get_filename()
                
                # 是否有附件
                if filename:
                    decode_header = email.header.decode_header(filename)
                    file_name = decode_header[0][0]
                    file_encoding = decode_header[0][1]
                    
                    if isinstance(file_name, bytes):
                        file_name = file_name.decode(file_encoding or 'utf-8')
                    
                    data = part.get_payload(decode=True)
                    
                    # 保存附件
                    if file_name and save_path:
                        self.save_file(file_name, data, save_path)
                        files.append(file_name)
                else:
                    # 处理正文
                    if part.get_charsets() is None:
                        charset = 'utf-8'
                    else:
                        charset = part.get_charsets()[0] or 'utf-8'
                    
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            message_content = payload.decode(charset)
                    except Exception as e:
                        # 尝试其他编码
                        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                            try:
                                message_content = payload.decode(enc)
                                break
                            except:
                                continue
        
        return {
            'content': message_content,
            'content_type': content_type,
            'files': files
        }
    
    def read_emails(self, count: int = 1, message_type: str = "Unseen", last_message: bool = True) -> List[EmailMessage]:
        """读取邮件"""
        emails = []
        imap_server = None
        
        try:
            imap_server = self.login_imap()
            
            # 选中收件箱
            select_status, info = imap_server.select(mailbox='INBOX')
            if select_status != 'OK':
                raise Exception(f"Failed to select inbox: {info}")
            
            # 选择邮件类型
            search_status, items = imap_server.search(None, message_type)
            if search_status != 'OK':
                raise Exception(f"Failed to search emails: {items}")
            
            message_ids = items[0].split()
            total = len(message_ids)
            
            if last_message:
                # 只读取最新的count封邮件
                message_list = message_ids[-count:] if count <= total else message_ids
            else:
                # 读取最旧的count封邮件
                message_list = message_ids[:count] if count <= total else message_ids
            
            for message_id in message_list:
                fetch_status, message = imap_server.fetch(message_id, "(RFC822)")
                if fetch_status != 'OK':
                    continue
                
                msg = email.message_from_bytes(message[0][1])
                
                # 消息日期
                date = self.format_date(msg['Date'])
                
                # 消息主题
                subject_parts = email.header.decode_header(msg["Subject"])
                subject = ""
                for part, encoding in subject_parts:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or 'utf-8')
                    else:
                        subject += part
                
                # 发件人
                from_parts = email.header.decode_header(msg["From"])
                sender = ""
                for part, encoding in from_parts:
                    if isinstance(part, bytes):
                        sender += part.decode(encoding or 'utf-8')
                    else:
                        sender += part
                
                # 收件人
                to_parts = email.header.decode_header(msg["To"])
                receiver = ""
                for part, encoding in to_parts:
                    if isinstance(part, bytes):
                        receiver += part.decode(encoding or 'utf-8')
                    else:
                        receiver += part
                
                # 解析邮件正文和附件
                msg_data = self.parse_message(msg, save_path=self.config.save_path)
                
                # 创建邮件消息对象
                email_msg = EmailMessage(
                    date=date,
                    subject=subject,
                    sender=sender,
                    receiver=receiver,
                    content=msg_data['content'],
                    content_type=msg_data['content_type'],
                    files=msg_data['files']
                )
                
                emails.append(email_msg)
                
        except Exception as e:
            raise
        finally:
            if imap_server:
                imap_server.logout()
        
        return emails
    
    def send_email(self, to: str, subject: str, content: str, content_type: str = 'plain', attachments: List[str] = None) -> bool:
        """发送邮件"""
        if attachments is None:
            attachments = []
            
        smtp_server = None
        
        try:
            smtp_server = self.login_smtp()
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config.username
            msg['To'] = to
            msg['Subject'] = email.header.Header(subject, 'utf-8').encode()
            
            # 添加正文
            msg.attach(MIMEText(content, content_type, 'utf-8'))
            
            # 添加附件
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, 'rb') as f:
                        part = email.mime.base.MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        email.encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                        msg.attach(part)
            
            # 发送邮件
            smtp_server.send_message(msg)
            return True
            
        except Exception as e:
            raise
        finally:
            if smtp_server:
                smtp_server.quit()


# 创建MCP服务实例
mcp = FastMCP(
    name="MCP Email Service"
)

# 初始化邮件配置
config = EmailConfig()
# 创建邮件服务实例
email_service = EmailService(config)


@mcp.tool
def read_emails(params: ReadEmailsParams=ReadEmailsParams(count=3, type='ALL', latest=True)) -> List[EmailMessage]:
    """
    读取邮件
    
    :param params: 读取邮件参数
    :type params: ReadEmailsParams
    
    :param params.count: 读取邮件数量，默认3条
    :type params.count: int, optional
    
    :param params.type: 读取邮件类型，默认ALL，可选值为ALL、UNREAD、READ
    :type params.type: str, optional
    
    :param params.latest: 是否读取最新邮件，默认True
    :type params.latest: bool, optional
    
    :return: 邮件消息列表
    :rtype: List[EmailMessage]
    """
    return email_service.read_emails(params.count, params.type, params.latest)


@mcp.tool
def send_email(params: SendEmailParams=SendEmailParams(to='收件人', subject='邮件主题', content='邮件内容', content_type='plain', attachments=[])) -> Dict[str, bool]:
    """
    发送邮件
    
    :param params: 发送邮件参数
    :type params: SendEmailParams
    
    :param params.to: 收件人邮箱地址
    :type params.to: str
    
    :param params.subject: 邮件主题
    :type params.subject: str
    
    :param params.content: 邮件内容
    :type params.content: str
    
    :param params.content_type: 邮件内容类型，默认plain，可选值为plain、html
    :type params.content_type: str, optional
    
    :param params.attachments: 附件路径列表，默认空列表
    :type params.attachments: List[str], optional
    
    :return: 发送结果，包含success键值对，值为True表示发送成功，False表示发送失败
    :rtype: Dict[str, bool]
    """
    success = email_service.send_email(
        to=params.to,
        subject=params.subject,
        content=params.content,
        content_type=params.content_type,
        attachments=params.attachments
    )
    return {"success": success}


if __name__ == "__main__":
    mcp.run()
