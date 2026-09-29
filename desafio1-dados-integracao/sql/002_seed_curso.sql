INSERT INTO core.curso (id_curso, nome, carga_horaria) VALUES
    ('C01', 'Onboarding Institucional EDEPE', 20),
    ('C02', 'LGPD Aplicada ao Serviço Público', 12),
    ('C03', 'Atendimento ao Público e Direitos Humanos', 16),
    ('C04', 'Introdução ao Processo Judicial Eletrônico', 24),
    ('C05', 'Ética e Conduta no Serviço Público', 8),
    ('C06', 'Acessibilidade Digital', 10),
    ('C07', 'Segurança da Informação Básica', 6)
ON CONFLICT (id_curso) DO NOTHING;
