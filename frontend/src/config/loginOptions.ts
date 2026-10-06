export const CATEGORIES = ['Partner', 'Client', 'Vendor'] as const;

const ROLE_PERSONAS = [
  { value: 'role-01', label: 'Role 01 – CC Customer', defined: true },
  { value: 'role-02', label: 'Role 02 – CC Inventory', defined: true },
  { value: 'role-03', label: 'Role 03 – CC Warranty', defined: true },
  { value: 'role-04', label: 'Role 04 – BO Customer', defined: true },
  { value: 'role-05', label: 'Role 05 – BO Inventory', defined: true },
  { value: 'role-06', label: 'Role 06 – BO Warranty', defined: true },
  { value: 'role-07', label: 'Role 07 – CC Manager', defined: true },
  { value: 'role-08', label: 'Role 08 – BO Manager', defined: true },
  { value: 'role-09', label: 'Role 09 – Operations Manager', defined: true },
  { value: 'role-10', label: 'Role 10 – Quality Analyst', defined: true },
  { value: 'role-11', label: 'Role 11 – Admin Executive', defined: true },
  { value: 'role-12', label: 'Role 12 – Surgeon', defined: true },
  { value: 'role-13', label: 'Role 13 – Office Manager', defined: true },
  { value: 'role-14', label: 'Role 14 – Sales Rep', defined: true },
  { value: 'role-15', label: 'Role 15 – CSR', defined: true },
  { value: 'role-16', label: 'Role 16 – Patient', defined: true },
  { value: 'role-17', label: 'Role 17 – Manager', defined: true },
] as const;

export const PERSONAS = ROLE_PERSONAS.map((persona) => {
  const roleNumber = persona.value.slice(-2);
  return {
    ...persona,
    demoEmail: `role${roleNumber}@local.dev`,
    demoPassword: `role${roleNumber}-demo`,
  };
});