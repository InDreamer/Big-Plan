---
- name: MLS Server Restore
  hosts: all
  become: yes
  vars:
    backup_path: "/appmls/osupgrade"
    error_log_path: "/var/log/ansible_restore_errors.log"

  tasks:
    - name: Ensure error log file exists
      file:
        path: "{{ error_log_path }}"
        state: touch
        mode: '0644'

    - name: Restore directories
      block:
        - unarchive:
            src: "{{ backup_path }}/{{ item.name }}.tar.gz"
            dest: "{{ item.path | dirname }}"
            remote_src: yes
          loop:
            - { name: 'mwmls', path: '/home/mwmls' }
            - { name: 'misdev', path: '/home/misdev' }
            - { name: 'astroidstp', path: '/home/astroidstp' }
            - { name: 'imftuser28', path: '/home/imftuser28' }
            - { name: 'itrs_home', path: '/home/itrs' }
            - { name: 'rc_d', path: '/etc/rc.d' }
            - { name: 'postfix', path: '/etc/postfix' }
            - { name: 'limits_d_security', path: '/etc/security/limits.d' }
            - { name: 'ITRS', path: '/opt/ITRS' }
      rescue:
        - name: Log directory restore error
          lineinfile:
            path: "{{ error_log_path }}"
            line: "{{ ansible_date_time.iso8601 }} - Error restoring directory: {{ item.name }} - {{ ansible_failed_result.msg }}"
          loop: "{{ ansible_failed_task.loop_items }}"

    - name: Restore individual files
      block:
        - unarchive:
            src: "{{ backup_path }}/{{ item.name }}.gz"
            dest: "{{ item.path | dirname }}"
            remote_src: yes
          loop:
            - { name: 'passwd', path: '/etc/passwd' }
            - { name: 'group', path: '/etc/group' }
            - { name: 'shadow', path: '/etc/shadow' }
            - { name: 'gshadow', path: '/etc/gshadow' }
            - { name: 'hosts', path: '/etc/hosts' }
            - { name: 'network', path: '/etc/sysconfig/network' }
            - { name: 'sysctl.conf', path: '/etc/sysctl.conf' }
            - { name: 'limits.conf', path: '/etc/security/limits.conf' }
            - { name: 'access.conf', path: '/etc/security/access.conf' }
            - { name: 'cron.allow', path: '/etc/cron.allow' }
      rescue:
        - name: Log file restore error
          lineinfile:
            path: "{{ error_log_path }}"
            line: "{{ ansible_date_time.iso8601 }} - Error restoring file: {{ item.name }} - {{ ansible_failed_result.msg }}"
          loop: "{{ ansible_failed_task.loop_items }}"

    - name: Restore SSH host keys
      unarchive:
        src: "{{ backup_path }}/ssh_host_keys.tar.gz"
        dest: "/etc/ssh/"
        remote_src: yes

    - name: Restore network scripts
      unarchive:
        src: "{{ backup_path }}/network_scripts.tar.gz"
        dest: "/etc/sysconfig/network-scripts/"
        remote_src: yes

    - name: Restore mail spool
      unarchive:
        src: "{{ backup_path }}/mail_mwmls.tar.gz"
        dest: "/var/spool/mail/"
        remote_src: yes

    - name: Restore cron
      unarchive:
        src: "{{ backup_path }}/cron.tar.gz"
        dest: "/var/spool/"
        remote_src: yes

    - name: Set correct ownership and permissions
      block:
        - file:
            path: "{{ item.path }}"
            owner: "{{ item.owner }}"
            group: "{{ item.group }}"
            mode: "{{ item.mode }}"
          loop:
            - { path: '/etc/passwd', owner: 'root', group: 'root', mode: '0644' }
            - { path: '/etc/group', owner: 'root', group: 'root', mode: '0644' }
            - { path: '/etc/shadow', owner: 'root', group: 'root', mode: '0000' }
            - { path: '/etc/gshadow', owner: 'root', group: 'root', mode: '0000' }
            - { path: '/etc/hosts', owner: 'root', group: 'root', mode: '0644' }
            - { path: '/etc/sysconfig/network', owner: 'root', group: 'root', mode: '0644' }
            - { path: '/etc/sysctl.conf', owner: 'root', group: 'root', mode: '0600' }
            - { path: '/etc/security/limits.conf', owner: 'root', group: 'root', mode: '0644' }
            - { path: '/etc/security/access.conf', owner: 'root', group: 'root', mode: '0644' }
            - { path: '/etc/cron.allow', owner: 'root', group: 'root', mode: '0644' }
      rescue:
        - name: Log permission setting error
          lineinfile:
            path: "{{ error_log_path }}"
            line: "{{ ansible_date_time.iso8601 }} - Error setting permissions: {{ item.path }} - {{ ansible_failed_result.msg }}"
          loop: "{{ ansible_failed_task.loop_items }}"

    - name: Display error log contents
      command: cat {{ error_log_path }}
      register: error_log_contents

    - name: Show error log
      debug:
        var: error_log_contents.stdout_lines