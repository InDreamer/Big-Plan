项目结构如下：

```
mars-server-management/
├── ansible.cfg
├── inventory
├── site.yml
└── roles/
    ├── MarsBackup/
    │   ├── tasks/
    │   │   └── main.yml
    │   └── vars/
    │       └── main.yml
    ├── MarsRestore/
    │   ├── tasks/
    │   │   └── main.yml
    │   └── vars/
    │       └── main.yml
    └── MLSUserGroup/
        ├── tasks/
        │   └── main.yml
        └── vars/
            └── main.yml
```

1. 主playbook (site.yml):

```yaml
---
- name: MLS Server Management
  hosts: mls_servers
  become: yes
  roles:
    - MLSUserGroup
    - MarsBackup
    - MarsRestore
```

2. Inventory文件 (inventory):

```ini
[mls_servers]
uklvadapp345 ansible_host=<your_server_ip>
```

3. MLSUserGroup 角色 (roles/MLSUserGroup/tasks/main.yml):

```yaml
---
# 创建组
- name: Create required groups
  group:
    name: "{{ item.name }}"
    gid: "{{ item.gid }}"
  loop:
    - { name: swapswire, gid: 18551001 }
    - { name: oinstall, gid: 56 }
    - { name: mlsdev, gid: 9250 }
    - { name: imft, gid: 8025 }
    - { name: astroidstp, gid: 9253 }
    - { name: itrs, gid: 102 }

# 创建用户
- name: Create required users
  user:
    name: "{{ item.name }}"
    uid: "{{ item.uid }}"
    group: "{{ item.group }}"
    groups: "{{ item.groups | default(omit) }}"
    home: "{{ item.home }}"
    shell: /bin/bash
    comment: "{{ item.comment }}"
  loop:
    - { name: mwmls, uid: 18551000, group: 18551001, home: /home/mwmls, comment: "mwmls ID" }
    - { name: oracle, uid: 9245, group: 56, home: /home/oracle, comment: "" }
    - { name: mlsdev, uid: 9250, group: 9250, home: /home/mlsdev, comment: "INC0000058031480" }
    - { name: imftuser28, uid: 6033, group: 8025, home: /home/imftuser28, comment: "FILEIT ID" }
    - { name: astroidstp, uid: 9252, group: 9253, home: /home/astroidstp, comment: "ASTROID SFTP ID" }
    - { name: itrs, uid: 18558003, group: 102, home: /home/itrs, comment: "" }

# 添加用户到额外的组
- name: Add users to additional groups
  user:
    name: "{{ item.user }}"
    groups: "{{ item.groups }}"
    append: yes
  loop:
    - { user: oinstall, groups: tideway }
    - { user: mwmls, groups: imft }
    - { user: mwmls, groups: astroidstp }

# 设置用户密码
- name: Set user passwords
  user:
    name: "{{ item.name }}"
    password: "{{ item.password | password_hash('sha512') }}"
  loop:
    - { name: mwmls, password: "{{ mwmls_password }}" }
    - { name: mlsdev, password: "{{ mlsdev_password }}" }
    - { name: itrs, password: "{{ itrs_password }}" }
    - { name: imftuser28, password: "{{ imftuser28_password }}" }
    - { name: astroidstp, password: "{{ astroidstp_password }}" }
    - { name: oracle, password: "{{ oracle_password }}" }
```

4. MarsBackup 角色 (roles/MarsBackup/tasks/main.yml):

```yaml
---
- name: Set umask
  shell: umask 022

- name: Ensure backup directory exists
  file:
    path: "{{ backup_path }}"
    state: directory
    mode: '0755'

- name: Backup home directories
  archive:
    path: "/home/{{ item }}"
    dest: "{{ backup_path }}/{{ item }}.tar.gz"
    format: gz
  loop:
    - mwmls
    - mlsdev
    - astroidstp
    - imftuser28
    - itrs
  register: home_backup

- name: Log home backup errors
  copy:
    content: "{{ item.stderr }}"
    dest: "{{ backup_path }}/{{ item.item }}_errors.log"
  when: item.failed
  loop: "{{ home_backup.results }}"

- name: Backup etc information
  archive:
    path: "{{ item.path }}"
    dest: "{{ backup_path }}/{{ item.name }}.tar.gz"
    format: gz
  loop:
    - { name: 'passwd', path: '/etc/passwd' }
    - { name: 'group', path: '/etc/group' }
    - { name: 'shadow', path: '/etc/shadow' }
    - { name: 'gshadow', path: '/etc/gshadow' }
    - { name: 'ssh', path: '/etc/ssh/ssh_host*' }
    - { name: 'rc_d', path: '/etc/rc.d' }
    - { name: 'hosts', path: '/etc/hosts' }
    - { name: 'postfix', path: '/etc/postfix' }
    - { name: 'network_ifcfg', path: '/etc/sysconfig/network-scripts/ifcfg*' }
    - { name: 'network', path: '/etc/sysconfig/network' }
    - { name: 'sysctl', path: '/etc/sysctl.*' }
    - { name: 'limitsconf_etc_security', path: '/etc/security/limits.conf' }
    - { name: 'access', path: '/etc/security/access.conf' }
    - { name: 'limits_d_security', path: '/etc/security/limits.d' }
    - { name: 'cron_allow', path: '/etc/cron.allow' }
  register: etc_backup

- name: Log etc backup errors
  copy:
    content: "{{ item.stderr }}"
    dest: "{{ backup_path }}/{{ item.item.name }}_errors.log"
  when: item.failed
  loop: "{{ etc_backup.results }}"

- name: Backup mail and cron information
  archive:
    path: "{{ item.path }}"
    dest: "{{ backup_path }}/{{ item.name }}.tar.gz"
    format: gz
  loop:
    - { name: 'mail', path: '/var/spool/mail/mwmls' }
    - { name: 'cron', path: '/var/spool/cron' }
  register: mail_cron_backup

- name: Log mail and cron backup errors
  copy:
    content: "{{ item.stderr }}"
    dest: "{{ backup_path }}/{{ item.item.name }}_errors.log"
  when: item.failed
  loop: "{{ mail_cron_backup.results }}"

- name: Backup ITRS
  archive:
    path: "/opt/ITRS"
    dest: "{{ backup_path }}/itrs.tar.gz"
    format: gz
  register: itrs_backup

- name: Log ITRS backup errors
  copy:
    content: "{{ itrs_backup.stderr }}"
    dest: "{{ backup_path }}/itrs_errors.log"
  when: itrs_backup.failed

- name: Set ownership of backup files
  file:
    path: "{{ backup_path }}"
    owner: mwmls
    group: swapswire
    recurse: yes

- name: Set permissions on backup files
  file:
    path: "{{ backup_path }}"
    mode: '0777'
    recurse: yes
```

5. MarsRestore 角色 (roles/MarsRestore/tasks/main.yml):

```yaml
---
- name: Ensure restore directory exists
  file:
    path: "{{ backup_path }}"
    state: directory
    mode: '0755'

- name: Restore home directories
  unarchive:
    src: "{{ backup_path }}/{{ item }}.tar.gz"
    dest: /
    remote_src: yes
  loop:
    - mwmls
    - mlsdev
    - astroidstp
    - imftuser28
    - itrs_home
  register: home_restore

- name: Log home restore errors
  copy:
    content: "{{ item.stderr }}"
    dest: "{{ backup_path }}/{{ item.item }}_restore_errors.log"
  when: item.failed
  loop: "{{ home_restore.results }}"

- name: Restore etc information
  unarchive:
    src: "{{ backup_path }}/{{ item }}.tar.gz"
    dest: /
    remote_src: yes
  loop:
    - ssh
    - rc_d
    - hosts
    - postfix
    - network_ifcfg
    - network
    - sysctl
    - limitsconf_etc_security
    - access
    - limits_d_security
    - cron_allow
  register: etc_restore

- name: Log etc restore errors
  copy:
    content: "{{ item.stderr }}"
    dest: "{{ backup_path }}/{{ item.item }}_restore_errors.log"
  when: item.failed
  loop: "{{ etc_restore.results }}"

- name: Restore mail and cron information
  unarchive:
    src: "{{ backup_path }}/{{ item }}.tar.gz"
    dest: /
    remote_src: yes
  loop:
    - mail
    - cron
  register: mail_cron_restore

- name: Log mail and cron restore errors
  copy:
    content: "{{ item.stderr }}"
    dest: "{{ backup_path }}/{{ item.item }}_restore_errors.log"
  when: item.failed
  loop: "{{ mail_cron_restore.results }}"

- name: Restore ITRS
  unarchive:
    src: "{{ backup_path }}/itrs.tar.gz"
    dest: /
    remote_src: yes
  register: itrs_restore

- name: Log ITRS restore errors
  copy:
    content: "{{ itrs_restore.stderr }}"
    dest: "{{ backup_path }}/itrs_restore_errors.log"
  when: itrs_restore.failed

- name: Set permissions on restored files
  file:
    path: "{{ backup_path }}"
    mode: '0777'
    recurse: yes
```

6. 各角色的 vars/main.yml 文件:

对于 MLSUserGroup:

```yaml
---
mwmls_password: "your_encrypted_password_here"
mlsdev_password: "your_encrypted_password_here"
itrs_password: "your_encrypted_password_here"
imftuser28_password: "your_encrypted_password_here"
astroidstp_password: "your_encrypted_password_here"
oracle_password: "your_encrypted_password_here"
```

对于 MarsBackup 和 MarsRestore:

```yaml
---
backup_path: /appmls/osupgrade/
```

要运行这个完整的 Ansible 项目：

1. 确保你的 `ansible.cfg` 文件配置正确。
2. 在 `inventory` 文件中设置正确的服务器 IP 或主机名。
3. 运行以下命令：

```
ansible-playbook -i inventory site.yml
```

这个 Ansible 项目现在包含了用户创建、备份和还原功能。你可以根据需要调整各个角色的执行顺序或单独运行特定的角色。

请注意，在实际使用之前，你应该仔细检查所有的任务和变量，确保它们符合你的具体需求和环境。特别是密码和敏感信息，建议使用 Ansible Vault 进行加密。