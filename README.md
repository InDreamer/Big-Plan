- name: Restore users with original passwords
  hosts: target_servers
  become: yes
  vars:
    user_groups:
      - { name: swapswire, gid: 18551001 }
      - { name: oinstall, gid: 56 }
      - { name: misdev, gid: 9250 }
      - { name: imft, gid: 8025 }
      - { name: astroidstp, gid: 9253 }
      - { name: itrs, gid: 102 }
    users:
      - { name: mwmls, uid: 18551000, group: 18551001, comment: "mwmls ID" }
      - { name: oracle, uid: 9245, group: 56, comment: "" }
      - { name: misdev, uid: 9250, group: 9250, comment: "INC0000058031" }
      - { name: imftuser28, uid: 6033, group: 8025, comment: "FILEIT ID" }
      - { name: astroidstp, uid: 9252, group: 9253, comment: "ASTROID SFTP ID" }
      - { name: itrs, uid: 18558003, group: 102, comment: "" }

  tasks:
    - name: Ensure required groups exist
      group:
        name: "{{ item.name }}"
        gid: "{{ item.gid }}"
      loop: "{{ user_groups }}"

    - name: Read password hashes from file
      local_action:
        module: slurp
        src: "./password_hashes.txt"
      register: password_file

    - name: Parse password hashes
      set_fact:
        password_hashes: "{{ password_file['content'] | b64decode | split('\n') | map('split', ':') | list }}"

    - name: Restore users with original password hashes
      user:
        name: "{{ item.0.name }}"
        uid: "{{ item.0.uid }}"
        group: "{{ item.0.group }}"
        groups: "{{ item.0.groups | default(omit) }}"
        comment: "{{ item.0.comment | default(omit) }}"
        home: "/home/{{ item.0.name }}"
        shell: /bin/bash
        password: "{{ item.1[1] }}"
      loop: "{{ users | zip(password_hashes) | list }}"

    - name: Add users to additional groups
      user:
        name: "{{ item.user }}"
        groups: "{{ item.group }}"
        append: yes
      loop:
        - { user: oinstall, group: tideway }
        - { user: mwmls, group: imft }
        - { user: mwmls, group: astroidstp }