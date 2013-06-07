%{!?_initddir: %{expand: %%global _initddir %{_initrddir}}}
%if 0%{?rhel} == 5
%global _sharedstatedir %{_localstatedir}/lib
%endif

%global sslcert %{_sysconfdir}/pki/tls/certs/prosody.crt
%global sslkey %{_sysconfdir}/pki/tls/private/prosody.key

%global luaver 5.2
%global pretag rc2

Name:           prosody
Version:        0.9.0
Release:        0.2.%{pretag}%{?dist}
Summary:        Flexible communications server for Jabber/XMPP

Group:          System Environment/Daemons
License:        MIT
URL:            http://prosody.im/
Source0:        http://prosody.im/tmp/%{version}%{?pretag}/%{name}-%{version}%{?pretag}.tar.gz
Source1:        %{name}.init
Source2:        %{name}.tmpfiles
Source3:        %{name}.service
Patch0:         %{name}.config.patch
Patch1:         %{name}.sslcerts.patch
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildRequires:  lua-devel
BuildRequires:  libidn-devel
BuildRequires:  openssl-devel
%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7
BuildRequires:  systemd-units
%endif
Requires:  lua-expat
Requires:  lua-sec
Requires:  lua-filesystem
Requires:  lua-dbi
%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units
%endif
%if 0%{?fedora} >= 16 || 0%{?rhel} >= 7
Requires: lua(abi) = %{luaver}
%else
Requires: lua >= %{luaver}
%endif

%description
Prosody is a flexible communications server for Jabber/XMPP  written in Lua.
It aims to be easy to use, and light on resources. For developers it aims
to be easy to extend and give a flexible system on which to rapidly 
develop added functionality, or prototype new protocols.


%prep
%setup -q -n %{name}-%{version}%{?pretag}
%patch0 -p1
# remove default ssl certificates
%patch1 -p1
#do the sed atfer patch1, to avoid a i686 build issue
sed -e 's|$(PREFIX)/lib|$(PREFIX)/%{_lib}|' -i Makefile
rm -rf certs/
# fix wrong end of line encoding
pushd doc
sed -i -e 's|\r||g' stanza.txt session.txt roster_format.txt
popd


%build
./configure \
  --with-lua='' \
  --with-lua-include=%{_includedir} \
  --prefix=%{_prefix}
make %{?_smp_mflags} CFLAGS="$RPM_OPT_FLAGS -fPIC"


%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT
#fix perms
chmod -x $RPM_BUILD_ROOT%{_libdir}/%{name}/%{name}.version
#avoid rpmlint unstripped-binary-or-object warnings
chmod 0755 $RPM_BUILD_ROOT%{_libdir}/%{name}/util/*.so

#directories for datadir and pids
mkdir -p $RPM_BUILD_ROOT%{_sharedstatedir}/%{name}
chmod 0755 $RPM_BUILD_ROOT%{_sharedstatedir}/%{name}
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/run/%{name}

%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7
#systemd stuff
mkdir -p $RPM_BUILD_ROOT%{_unitdir}
install -p -m 644 %{SOURCE3} $RPM_BUILD_ROOT%{_unitdir}/%{name}.service

#tmpfiles.d stuff
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/tmpfiles.d
install -p -m 644 %{SOURCE2} $RPM_BUILD_ROOT%{_sysconfdir}/tmpfiles.d/%{name}.conf
%else
#install initd script
mkdir -p $RPM_BUILD_ROOT%{_initddir}
install -m755 %{SOURCE1} $RPM_BUILD_ROOT%{_initddir}/%{name}
%endif


%clean
rm -rf $RPM_BUILD_ROOT


%pre
%{_sbindir}/useradd -d %{_sharedstatedir}/%{name} -r -s /sbin/nologin %{name} 2> /dev/null || :


%preun
%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7
%systemd_preun %{name}.service
%else
if [ $1 = 0 ]; then
    # Package removal, not upgrade
    service %{name} stop > /dev/null 2>&1 || :
    chkconfig --del %{name} || :
fi
%endif

%post
%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7
%systemd_post %{name}.service
%else
if [ $1 -eq 1 ] ; then
    # Initial installation
    chkconfig --add %{name} || :
fi
%endif
umask 077
if [ ! -f %{sslkey} ] ; then
%{_bindir}/openssl genrsa 1024 > %{sslkey} 2> /dev/null
chown root:%{name} %{sslkey}
chmod 640 %{sslkey}
fi

FQDN=`hostname`
if [ "x${FQDN}" = "x" ]; then
   FQDN=localhost.localdomain
fi

if [ ! -f %{sslcert} ] ; then
cat << EOF | %{_bindir}/openssl req -new -key %{sslkey} \
         -x509 -days 365 -set_serial $RANDOM \
         -out %{sslcert} 2>/dev/null
--
SomeState
SomeCity
SomeOrganization
SomeOrganizationalUnit
${FQDN}
root@${FQDN}
EOF
chmod 644 %{sslcert}
fi


%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7
%postun
%systemd_postun_with_restart %{name}.service
%endif


%files
%defattr(-,root,root,-)
%doc AUTHORS COPYING HACKERS README TODO doc/*
%{_bindir}/%{name}
%{_bindir}/%{name}ctl
%dir %{_libdir}/%{name}
%{_libdir}/%{name}/*
%dir %{_sysconfdir}/%{name}
%config(noreplace) %attr(0640, root, %{name}) %{_sysconfdir}/%{name}/*
%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7
%config(noreplace) %{_sysconfdir}/tmpfiles.d/%{name}.conf
%{_unitdir}/%{name}.service
%else
%{_initddir}/%{name}
%endif
%{_mandir}/man1/*.1.gz
%dir %attr(-, %{name}, %{name}) %{_sharedstatedir}/%{name}
%dir %attr(-, %{name}, %{name}) %{_localstatedir}/run/%{name}


%changelog
* Fri Jun 07 2013 Johan Cwiklinski <johan AT x-tnd DOT be> - 0.9.0-0.2.rc2
- Update to 0.9.0rc2

* Wed May 15 2013 Tom Callaway <spot@fedoraproject.org> - 0.9.0-0.1.beta1
- update to 0.9.0beta1, rebuild for lua 5.2

* Sat Apr 27 2013 Robert Scheck <robert@fedoraproject.org> - 0.8.2-9
- Apply wise permissions to %%{_sysconfdir}/%%{name} (#955384)
- Apply wise permissions to default SSL certificates (#955380)
- Do not ship %%{_sysconfdir}/%%{name}/certs by default (#955385)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.2-8
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Thu Sep 27 2012 Johan Cwiklinski <johan At x-tnd DOt be> 0.8.2-7
- Use systemd-rpm macros, bz #850282

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.8.2-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon May 07 2012 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.2-5
- Missing rhel %%ifs
- Change the way SSL certificate is generated

* Sun May 06 2012 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.2-4
- ghost %%{_localstatedir}/run/%%{name}

* Sun May 06 2012 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.2-3
- Add missing requires
- Add rhel %%ifs

* Mon Mar 05 2012 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.2-2
- Switch to systemd for Fedora >= 15, keep sysv for EPEL builds
- Remove some macros that should not be used

* Thu Jun 23 2011 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.2-1.trashy
- 0.8.2

* Tue Jun 7 2011 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.1-1.trashy
- 0.8.1

* Sun May 8 2011 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.0-3.trashy
- tmpfiles.d configuration for F-15

* Sat Apr 16 2011 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.0-2.trashy
- Now requires lua-dbi

* Fri Apr 8 2011 Johan Cwiklinski <johan AT x-tnd DOT be> 0.8.0-1.trashy
- 0.8.0

* Sun Jan 23 2011 Johan Cwiklinski <johan AT x-tnd DOT be> 0.7.0-4.trashy
- Redefine _initddir and _sharedstatedir marcos for EL-5

* Sat Dec 11 2010 Johan Cwiklinski <johan AT x-tnd DOT be> 0.7.0-3
- Apply ssl patch before sed on libdir; to avoid a patch context issue 
  building on i686 

* Sat Sep 11 2010 Johan Cwiklinski <johan AT x-tnd DOT be> 0.7.0-2
- No longer ships default ssl certificates, generates one at install

* Wed Jul 14 2010 Johan Cwiklinski <johan AT x-tnd DOT be> 0.7.0-1
- Update to 0.7.0

* Wed Apr 28 2010 Johan Cwiklinski <johan AT x-tnd DOT be> 0.6.2-1
- Update to 0.6.2

* Thu Dec 31 2009 Johan Cwiklinski <johan AT x-tnd DOT be> 0.6.1-1
- Initial packaging
