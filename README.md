---
- name: MLS Server Backup
  hosts: all
  become: yes
  vars:
    backup_path: "/appmls/osupgrade"
    error_log_path: "/var/log/ansible_backup_errors.log"

  tasks:
    - name: Ensure backup directory exists
      file:
        path: "{{ backup_path }}"
        state: directory
        mode: '0755'

    - name: Ensure error log file exists
      file:
        path: "{{ error_log_path }}"
        state: touch
        mode: '0644'

    - name: Backup home directories
      block:
        - archive:
            path: 
              - /home/mwmls
              - /home/misdev
              - /home/astroidstp
              - /home/imftuser28
              - /home/itrs
            dest: "{{ backup_path }}/{{ item }}.tar.gz"
            format: gz
          loop:
            - mwmls
            - misdev
            - astroidstp
            - imftuser28
            - itrs_home
      rescue:
        - name: Log home directory backup error
          lineinfile:
            path: "{{ error_log_path }}"
            line: "{{ ansible_date_time.iso8601 }} - Error backing up {{ item }} home directory"
          loop: "{{ ansible_failed_task.loop_items }}"

    - name: Backup etc information
      block:
        - archive:
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
            - { name: 'sysctl', path: '/etc/sysctl.conf' }
            - { name: 'limitsconf_etc_security', path: '/etc/security/limits.conf' }
            - { name: 'access', path: '/etc/security/access.conf' }
            - { name: 'limits_d_security', path: '/etc/security/limits.d' }
            - { name: 'cron_allow', path: '/etc/cron.allow' }
      rescue:
        - name: Log etc information backup error
          lineinfile:
            path: "{{ error_log_path }}"
            line: "{{ ansible_date_time.iso8601 }} - Error backing up {{ item.name }} ({{ item.path }})"
          loop: "{{ ansible_failed_task.loop_items }}"

    - name: Backup mail/cron information
      block:
        - archive:
            path: "{{ item.path }}"
            dest: "{{ backup_path }}/{{ item.name }}.tar.gz"
            format: gz
          loop:
            - { name: 'mail', path: '/var/spool/mail/mwmls' }
            - { name: 'cron', path: '/var/spool/cron' }
      rescue:
        - name: Log mail/cron backup error
          lineinfile:
            path: "{{ error_log_path }}"
            line: "{{ ansible_date_time.iso8601 }} - Error backing up {{ item.name }} ({{ item.path }})"
          loop: "{{ ansible_failed_task.loop_items }}"

    - name: Backup ITRS
      block:
        - archive:
            path: "/opt/ITRS"
            dest: "{{ backup_path }}/itrs.tar.gz"
            format: gz
      rescue:
        - name: Log ITRS backup error
          lineinfile:
            path: "{{ error_log_path }}"
            line: "{{ ansible_date_time.iso8601 }} - Error backing up ITRS (/opt/ITRS)"

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

    - name: Display error log contents
      command: cat {{ error_log_path }}
      register: error_log_contents

    - name: Show error log
      debug:
        var: error_log_contents.stdout_lines