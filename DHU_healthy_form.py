#!/bin/python3
'''
@author DCMMC
@date 2020/03/03
@license MIT
@email xwt97294597@gmail.com
'''
import requests
import re
import json
import datetime
import os
import logging
import coloredlogs
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from email.mime.text import MIMEText
from email.header import Header
from smtplib import SMTP_SSL
import time

logger = logging.getLogger('DHU healthy form tool')
coloredlogs.install()
# logger.setLevel(logging.DEBUG)
# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler)
fh = logging.FileHandler('DHU_healthy_form.log')
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

config_file = 'user_config.json'
login_url = 'http://wserver.dhu.edu.cn/index.do?method=login'
submit_url = 'http://fygrtb.dhu.edu.cn/pdc/formDesignApi/dataFormSave'
# must get with logined cookie
# !!! hardcoded app id: 36
# Refer to http://wserver.dhu.edu.cn/personApp.do?method=list
healthy_app_url = 'http://wserver.dhu.edu.cn/personApp.do?method=add&appid=36'
max_try = 30
UA = 'Mozilla/5.0 (X11; CrOS x86_64 12105.100.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.144 Safari/537.36'


def send_mail_qq(sender_qq, sender_auth_code, receiver, mail_title,
                 mail_content, *args, **kwargs):
    """
    simple mail sender using qq mail
    """
    host_server = 'smtp.qq.com'
    sender_qq_mail = sender_qq + '@qq.com'
    smtp = SMTP_SSL(host_server)
    smtp.ehlo(host_server)
    smtp.login(sender_qq, sender_auth_code)
    msg = MIMEText(mail_content.encode('utf-8'), "plain", 'utf-8')
    msg["Subject"] = Header(mail_title, 'utf-8')
    msg["From"] = sender_qq_mail
    msg["To"] = receiver
    smtp.sendmail(sender_qq_mail, receiver, msg.as_string())
    smtp.quit()


def send_mail(sender, sender_auth_code, receiver, mail_title, mail_content,
              *args, **kwargs):
    # Now that only support qq mail as server
    send_mail_qq(sender, sender_auth_code, receiver, mail_title, mail_content,
                 *args, **kwargs)


def send_mail_wrapper(sender, sender_auth_code, receiver, *args, **kwargs):
    def send_to(mail_title, mail_content, *args, **kwargs):
        send_mail(sender, sender_auth_code, receiver, mail_title, mail_content,
                  *args, **kwargs)

    return send_to


def get_history_submits(username, password, *args, **kwargs):
    """
    Login and then get history submits
    """
    login_res = requests.post(
        login_url,
        data={
            'openid': '',
            'url': 'query',
            'redi': '',
            'methV': 'courseTab',
            'userName': username,
            'passwd': password
        },
        headers={
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': UA,
            'Origin': 'http://wserver.dhu.edu.cn',
            'Content-Type': 'application/x-www-form-urlencoded',
            'DNT': '1',
            'Referer': 'http://wserver.dhu.edu.cn/index.do?method=login'
        })
    add_healthy_app = requests.get(
        healthy_app_url,
        headers={
            'Connection':
            'keep-alive',
            'Upgrade-Insecure-Requests':
            '1',
            'User-Agent':
            UA,
            'DNT':
            '1',
            'Accept':
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding':
            'gzip, deflate',
            'Accept-Language':
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ja;q=0.6',
        },
        cookies=login_res.cookies)
    if add_healthy_app.text.strip() == '1':
        logger.info('Install healthy app to user at first time.')
    elif add_healthy_app.text.strip() == '0':
        logger.info('This healthy app has already installed in the past.')
    else:
        logger.error('Unexcepted error when installing healthy app.')
    login_res = requests.post(
        login_url,
        data={
            'openid': '',
            'url': 'query',
            'redi': '',
            'methV': 'courseTab',
            'userName': username,
            'passwd': password
        },
        headers={
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': UA,
            'Origin': 'http://wserver.dhu.edu.cn',
            'Content-Type': 'application/x-www-form-urlencoded',
            'DNT': '1',
            'Referer': 'http://wserver.dhu.edu.cn/index.do?method=login'
        })
    fwd_link = re.search('"yymc":"疫情上报系统","fwlj":"(http[:/a-zA-Z0-9&=\.?]+)"',
                         login_res.text).group(1)
    logger.info('Login successful, forward link: {}'.format(fwd_link))
    formpage_res = requests.get(
        fwd_link,
        headers={
            'Connection':
            'keep-alive',
            'Cache-Control':
            'max-age=0',
            'Upgrade-Insecure-Requests':
            '1',
            'User-Agent':
            UA,
            'DNT':
            '1',
            'Accept':
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding':
            'gzip, deflate',
            'Accept-Language':
            'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ja;q=0.6',
        })
    selfFormWid = re.search("_selfFormWid = '([a-zA-Z0-9]+)'",
                            formpage_res.text).group(1)
    form_history_submit = json.loads(
        re.search('fillDetail = (.*);$', [
            l for l in formpage_res.text.split('\n') if 'fillDetail = ' in l
        ][0]).group(1))
    logger.info(
        'Load form page successful, wid: {}, forms of last submit: {}'.format(
            selfFormWid, form_history_submit[0]))
    return fwd_link, selfFormWid, form_history_submit


def verify(username, password, send_mail_instance, *args, **kwargs):
    """
    Ensure today has been submit successful one form
    """
    _, _, form_history_submit = get_history_submits(username, password)
    # format of CLRQ: "2020-03-03 18:11:36"
    last_submit_datetime = datetime.datetime.strptime(
        form_history_submit[0]['CLRQ'], '%Y-%m-%d %H:%M:%S')
    logger.info('last submit date: {}'.format(last_submit_datetime))
    send_mail_instance and send_mail_instance(
        mail_title='Successful submit by DHU healthy form tool',
        mail_content=
        ('Congratulations! Your healthy form has been ' +
         'submited successfully at {}!\n\n\n'.format(last_submit_datetime) +
         'Detail submited form contents of the last 3 days are shown below:\n\n'
         + json.dumps(form_history_submit, indent=2, ensure_ascii=False)))
    return len(form_history_submit) >= 1 and last_submit_datetime.date(
    ) == datetime.datetime.today().date()


def submit(username, password, send_mail_instance, *args, **kwargs):
    """
    Simulate submit a form according last valid submit
    """
    if 'try_cnt' not in kwargs:
        try_cnt = 0
    else:
        try_cnt = kwargs['try_cnt']
    try:
        fwd_link, selfFormWid, form_history_submit = get_history_submits(
            username, password)
        data = form_history_submit[0]
        del data['CLRQ']
        del data['USERID']
        data['DATETIME_CYCLE'] = datetime.datetime.now().strftime("%Y/%m/%d")
        logger.debug('New submit data constructed: {}'.format(data))
        submit_res = requests.post(
            submit_url + '?wid={}&userId={}'.format(selfFormWid, username),
            data=data,
            headers={
                'Origin':
                'http://fygrtb.dhu.edu.cn',
                'Accept-Encoding':
                'gzip, deflate',
                'Accept-Language':
                'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,ja;q=0.6',
                'User-Agent':
                UA,
                'Content-Type':
                'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept':
                'application/json, text/javascript, */*; q=0.01',
                'Referer':
                fwd_link,
                'X-Requested-With':
                'XMLHttpRequest',
                'Connection':
                'keep-alive',
                'DNT':
                '1',
            })
        if json.loads(submit_res.text)['result']:
            logger.info('Successful submit: {}'.format(data['DATETIME_CYCLE']))
            if verify(username, password, send_mail_instance):
                logger.info('Verify the submit successfully.')
            else:
                raise Exception('Verify the submit failed.')
        else:
            logger.error('Error submit.')
    except Exception as e:
        try_cnt += 1
        logger.exception('Exception raised when submit the new form')
        if try_cnt >= max_try:
            logger.error('Failed submit after {} tries.'.format(try_cnt))
            try:
                send_mail_instance and send_mail_instance(
                    mail_title='Submit failed by DHU healthy form tool',
                    mail_content=(
                        "It's very sorry to notice you that after {} tries." +
                        "\nYou must submit the healthy form manully!!"
                    ).format(try_cnt))
            except Exception as e:
                logger.error('error when send email! Exception:', e, exc_info=1)
            return 0
        else:
            logger.error('Continue try to submit the new form ({}/{}).'.format(
                try_cnt, max_try))
            try:
                send_mail_instance and send_mail_instance(
                    mail_title='Submit failed by DHU healthy form tool',
                    mail_content=
                    ("It's very sorry to notice you that after {} tries." +
                     "\nHowever, this tool is still try to submit again with no more than {} tries."
                     + "\nYou may need submit the healthy form manully.").format(
                         try_cnt, max_try))
            except Exception as e:
                logger.error('error when send email! Exception:', e, exc_info=1)
            time.sleep(60 + 60 * try_cnt)
            try:
                submit(username, password, send_mail_instance, try_cnt=try_cnt)
            except Exception as e:
                logger.error('error when retry to submit from last failed!',
                             'Exception:', e, exc_info=1)


def check_config(conf):
    logger.debug('start checking config')
    assert 'users' in conf
    assert len(conf['users']) >= 1
    assert all([
        all([user.get('username'), user.get('password')])
        for user in conf['users']
    ])
    if any([user.get('receiver_mail') for user in conf['users']]):
        assert conf.get('sender_qq') and conf.get('qq_auth_code')
    for user in conf['users']:
        if not 0 <= user.get('hour') < 9:
            logger.warn('The push time must between 00:00 to 8:59!')
        assert 0 <= user.get('hour', -1) <= 23
        assert 0 <= user.get('minute', -1) <= 59
    logger.debug('the config is valid')


if __name__ == '__main__':
    conf = None
    send_mail_instances = []
    test = False
    if os.path.isfile(config_file):
        try:
            with open(config_file) as f:
                conf = json.load(f)
                check_config(conf)
                for user in conf['users']:
                    logger.info(
                        'Push time for user {} is {}:{} every day.'.format(
                            user['username'], user['hour'], user['minute']))
                    if user.get('receiver_mail'):
                        send_mail_instances.append(
                            send_mail_wrapper(
                                sender=conf['sender_qq'],
                                sender_auth_code=conf['qq_auth_code'],
                                receiver=user['receiver_mail']))
                    else:
                        send_mail_instances.append(None)
        except Exception:
            conf = None
            logger.exception(
                'Exception raised when loading config, try to input config from stdin'
            )
        logger.info('Welcome: {}'.format(conf['users'][0]['username']))
    if not conf:
        test = True
        print('User config not found, please enter your student ID and',
              'password for campus Wifi in DHU:')
        username = input('Student ID: ')
        password = input('Password: ')
        if input(
                'Would you wanna use qq mail to receive the latest information '
                + 'about this form tool?\n' +
                'More info refers to https://service.mail.qq.com/' +
                'cgi-bin/help?subtype=1&id=28&no=1001256\n' +
                'Your answer: (y/n)') == 'y':
            qq = input('QQ number as sender: ')
            auth_code = input(
                'SMTP authorization code of corresponding QQ mail: ')
            if input(
                    'Do you want to use another mail as receiver for latest information? (y/n)'
            ) == 'y':
                receiver = input('Receiver mail: ')
            else:
                receiver = (qq + '@qq.com')
            send_mail_instance = send_mail_wrapper(
                sender=qq, sender_auth_code=auth_code, receiver=receiver)
            send_mail_instance(
                mail_title='Test by DHU healthy form tool',
                mail_content=
                'Congratulations! This email represents that your mail ' +
                'server is configured successfully!')
            send_mail_instances.append(send_mail_instance)
            logger.info('Testing your QQ mail by sending an email to {}...'.
                        format(qq + '@qq.com'))
        else:
            receiver = None
            qq, auth_code = None, None
            send_mail_instances.append(None)

        try:
            hour, minute = [
                int(i) for i in input(
                    'Push time (e.g. 0:10 or 8:30) 0:0 ~ 23:59:').split(':')
            ]
            conf = {
                'users': [{
                    'username': username,
                    'password': password,
                    'hour': hour,
                    'minute': minute,
                    'receiver_mail': receiver
                }],
                'sender_qq':
                qq,
                'qq_auth_code':
                auth_code
            }
            check_config(conf)
            with open(config_file, 'w') as f:
                json.dump(conf, f)
        except Exception:
            logger.exception(
                'Exception raised when input config from stdin, exit...')
            sys.exit(-1)
    if test:
        try:
            logger.info('Now testing submit.')
            for user in conf['users']:
                submit(
                    username=user['username'],
                    password=user['password'],
                    send_mail_instance=send_mail_instances[0])
        except Exception:
            logger.exception('Exception raised when testing submit, exit...')
            sys.exit(-1)
    # retry after 20s when job raised exceptions
    # Refer to https://www.cnblogs.com/quijote/p/4385774.html
    scheduler = BlockingScheduler(
        jobstore_retry_interval=20,
        job_defaults={
            'coalesce': True,
            'max_instances': len(conf['users']) * 2,
            'misfire_grace_time': 60 * 60 * 9
        })
    for i, user in enumerate(conf['users']):
        trigger1 = CronTrigger(hour=user['hour'], minute=user['minute'])
        scheduler.add_job(
            submit,
            trigger1,
            kwargs={
                'username': user['username'],
                'password': user['password'],
                'send_mail_instance': send_mail_instances[i]
            })
        trigger2 = CronTrigger(
            hour=user['hour'] + ((user['minute'] + 5) // 60),
            minute=((user['minute'] + 5) % 60))
        scheduler.add_job(
            submit,
            trigger2,
            kwargs={
                'username': user['username'],
                'password': user['password'],
                'send_mail_instance': send_mail_instances[i]
            })
    # blocking mode, i.e. infinite loop
    scheduler.start()
