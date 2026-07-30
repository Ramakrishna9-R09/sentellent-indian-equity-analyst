import {
  to = module.network.aws_vpc.this
  id = "vpc-006266d47edc90cc9"
}

import {
  to = module.network.aws_internet_gateway.this
  id = "igw-02f6f72734f0b0402"
}

import {
  to = module.network.aws_eip.nat
  id = "eipalloc-0abe892006fa38acb"
}

import {
  to = module.network.aws_nat_gateway.this
  id = "nat-08b5725054698f248"
}

import {
  to = module.network.aws_subnet.public["0"]
  id = "subnet-01a279b77fee0edba"
}

import {
  to = module.network.aws_subnet.public["1"]
  id = "subnet-0905d2f978c31370d"
}

import {
  to = module.network.aws_subnet.private["0"]
  id = "subnet-0921d114ecdf53ff2"
}

import {
  to = module.network.aws_subnet.private["1"]
  id = "subnet-016b64fc78d474660"
}

import {
  to = module.network.aws_route_table.public
  id = "rtb-0150d1ac238951a8a"
}

import {
  to = module.network.aws_route_table.private
  id = "rtb-01b4439bad856a419"
}

import {
  to = module.network.aws_route.public_internet
  id = "rtb-0150d1ac238951a8a_0.0.0.0/0"
}

import {
  to = module.network.aws_route.private_nat
  id = "rtb-01b4439bad856a419_0.0.0.0/0"
}

import {
  to = module.network.aws_route_table_association.public["0"]
  id = "subnet-01a279b77fee0edba/rtb-0150d1ac238951a8a"
}

import {
  to = module.network.aws_route_table_association.public["1"]
  id = "subnet-0905d2f978c31370d/rtb-0150d1ac238951a8a"
}

import {
  to = module.network.aws_route_table_association.private["0"]
  id = "subnet-0921d114ecdf53ff2/rtb-01b4439bad856a419"
}

import {
  to = module.network.aws_route_table_association.private["1"]
  id = "subnet-016b64fc78d474660/rtb-01b4439bad856a419"
}

import {
  to = module.network.aws_security_group.alb
  id = "sg-029d824d74ffa6d3c"
}

import {
  to = module.network.aws_security_group.ecs
  id = "sg-02fd559504b71c8ed"
}

import {
  to = module.network.aws_security_group.rds
  id = "sg-0ba5d9fca822ae061"
}

import {
  to = module.network.aws_vpc_security_group_ingress_rule.alb_http
  id = "sgr-0f5ac5ac43a4a692d"
}

import {
  to = module.network.aws_vpc_security_group_egress_rule.alb_egress
  id = "sgr-0f90aaba7113762c8"
}

import {
  to = module.network.aws_vpc_security_group_ingress_rule.ecs_from_alb["api"]
  id = "sgr-0cf127ab17fdfa29f"
}

import {
  to = module.network.aws_vpc_security_group_ingress_rule.ecs_from_alb["web"]
  id = "sgr-06aefe0b467bad3fa"
}

import {
  to = module.network.aws_vpc_security_group_egress_rule.ecs_egress
  id = "sgr-010bc63b426ad308d"
}

import {
  to = module.network.aws_vpc_security_group_ingress_rule.rds_from_ecs
  id = "sgr-003cae8a42146e8d4"
}

import {
  to = module.network.aws_vpc_security_group_egress_rule.rds_egress
  id = "sgr-02162e960edc0c055"
}
