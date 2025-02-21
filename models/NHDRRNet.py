import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models import resnet

config={
    'in_channel': 6,
    'hidden_dim': 32,
    'encoder_kernel_size': 3,
    'encoder_stride': 2,
    'triple_pass_filter': 256
}


class PaddedConv2d(nn.Module):
    def __init__(self, input_channels, output_channels, ks, stride):
        super().__init__()
        # Custom Padding Calculation
        if isinstance(ks, tuple):
            k_h, k_w = ks
        else:
            k_h = ks
            k_w = ks
        if isinstance(stride, tuple):
            s_h, s_w = stride
        else:
            s_h = stride
            s_w = stride
        pad_h, pad_w = k_h - s_h, k_w - s_w
        pad_up, pad_left = pad_h // 2, pad_w // 2
        pad_down, pad_right= pad_h - pad_up, pad_w - pad_left
        self.pad = nn.ZeroPad2d([pad_left, pad_right, pad_up, pad_down])
        self.conv = nn.Conv2d(input_channels, output_channels, kernel_size=ks, stride=stride, bias=True)

    def forward(self, x):
        x = self.pad(x)
        x = self.conv(x)
        return x


class NHDRRNet(nn.Module):
    def __init__(self) -> None:
        super(NHDRRNet, self).__init__()
        # self.filter = config.filter
        # self.encoder_kernel = config.encoder_kernel
        # self.decoder_kernel = config.decoder_kernel
        # self.triple_pass_filter = config.triple_pass_filter
        self.c_dim = 3

        self.encoder_1 = []
        self.encoder_2 = []
        self.encoder_3 = []
        self.encoder_1.append(self._make_encoder(config['in_channel'], config['hidden_dim']))
        self.encoder_1.append(self._make_encoder(config['hidden_dim'], config['hidden_dim'] * 2))
        self.encoder_1.append(self._make_encoder(config['hidden_dim'] * 2, config['hidden_dim'] * 4))
        self.encoder_1.append(self._make_encoder(config['hidden_dim'] * 4, config['hidden_dim'] * 8))
        self.encoder_1 = nn.ModuleList(self.encoder_1)

        self.encoder_2.append(self._make_encoder(config['in_channel'], config['hidden_dim']))
        self.encoder_2.append(self._make_encoder(config['hidden_dim'], config['hidden_dim'] * 2))
        self.encoder_2.append(self._make_encoder(config['hidden_dim'] * 2, config['hidden_dim'] * 4))
        self.encoder_2.append(self._make_encoder(config['hidden_dim'] * 4, config['hidden_dim'] * 8))
        self.encoder_2 = nn.ModuleList(self.encoder_2)

        self.encoder_3.append(self._make_encoder(config['in_channel'], config['hidden_dim']))
        self.encoder_3.append(self._make_encoder(config['hidden_dim'], config['hidden_dim'] * 2))
        self.encoder_3.append(self._make_encoder(config['hidden_dim'] * 2, config['hidden_dim'] * 4))
        self.encoder_3.append(self._make_encoder(config['hidden_dim'] * 4, config['hidden_dim'] * 8))
        self.encoder_3 = nn.ModuleList(self.encoder_3)

        self.final_encoder = nn.Sequential(
                                PaddedConv2d(config['hidden_dim'] * 8 * 3, config['triple_pass_filter'], 3, 1),
                                nn.BatchNorm2d(config['triple_pass_filter'], momentum=0.9),
                                nn.ReLU()
                            )
        self.triple_list = []
        for i in range(10):
            self.triple_list.append(nn.ModuleList(self._make_triple_pass_layer()))
        self.triple_list = nn.ModuleList(self.triple_list)
        self.avgpool = nn.AdaptiveAvgPool2d((16, 16))
        self.theta_conv = PaddedConv2d(config['triple_pass_filter'], 128, 1, 1)
        self.phi_conv = PaddedConv2d(config['triple_pass_filter'], 128, 1, 1)
        self.g_conv = PaddedConv2d(config['triple_pass_filter'], 128, 1, 1)
        self.theta_phi_g_conv = PaddedConv2d(config['triple_pass_filter']//2, config['triple_pass_filter'], 1, 1)
        self.decoder1 = self._make_decoder(config['triple_pass_filter'] * 2, config['hidden_dim'] * 4)
        self.decoder2 = self._make_decoder(config['hidden_dim'] * 4 * 4, config['hidden_dim'] * 2)
        self.decoder3 = self._make_decoder(config['hidden_dim'] * 2 * 4, config['hidden_dim'])
        self.decoder_final = nn.Sequential(
            nn.ConvTranspose2d(config['hidden_dim'] * 4, config['hidden_dim'], 4, 2, 1, bias=True),
            nn.BatchNorm2d(config['hidden_dim']),
            nn.LeakyReLU()
        )
        self.final = nn.Sequential(
            PaddedConv2d(config['hidden_dim'], 3, 3, 1),
            nn.Tanh()
        )

    def _make_encoder(self, in_c, out):
        encoder = nn.Sequential(
            PaddedConv2d(in_c, out, config['encoder_kernel_size'], config['encoder_stride']),
            nn.BatchNorm2d(out, momentum=0.9),
            nn.ReLU()
        )
        return encoder
    # def _make_encoder(self):
    #     encoder = nn.Sequential(
    #         PaddedConv2d(config['in_channel'], config['hidden_dim'], config['encoder_kernel_size'], config['encoder_stride']),
    #         nn.BatchNorm2d(),
    #         nn.ReLU(),
    #         PaddedConv2d(config['hidden_dim'], config['hidden_dim'] * 2, config['encoder_kernel_size'], config['encoder_stride']),
    #         nn.BatchNorm2d(),
    #         nn.ReLU(),
    #         PaddedConv2d(config['hidden_dim'] * 2, config['hidden_dim'] * 4, config['encoder_kernel_size'], config['encoder_stride']),
    #         nn.BatchNorm2d(),
    #         nn.ReLU(),
    #         PaddedConv2d(config['hidden_dim'] * 4, config['hidden_dim'] * 8, config['encoder_kernel_size'], config['encoder_stride']),
    #         nn.BatchNorm2d(),
    #         nn.ReLU()
    #     )
    #     return encoder

    def _make_decoder(self, in_c, out):
        decoder = nn.Sequential(
            nn.ConvTranspose2d(in_c, out, 4, 2, 1, bias=True),
            nn.BatchNorm2d(out),
            nn.LeakyReLU()
        )
        return decoder

    def _make_triple_pass_layer(self):
        return [PaddedConv2d(config['triple_pass_filter'], config['triple_pass_filter'], 1, 1),
                PaddedConv2d(config['triple_pass_filter'], config['triple_pass_filter'], 3, 1),
                PaddedConv2d(config['triple_pass_filter'], config['triple_pass_filter'], 5, 1),
                PaddedConv2d(config['triple_pass_filter'] * 3, config['triple_pass_filter'], 3, 1)]
    
    def triplepass(self, x, i):
        x1 = F.relu(self.triple_list[i][0](x))
        x2 = F.relu(self.triple_list[i][1](x))
        x3 = F.relu(self.triple_list[i][2](x))
        x3 = torch.cat([x1,x2,x3], dim=1)
        x4 = self.triple_list[i][3](x3)
        x5 = x4 + x

        return x5

    def global_non_local(self, x):
        b, c, h, w = x.shape
        theta = self.theta_conv(x).reshape(b, c//2, h * w).permute(0, 2, 1).contiguous()
        phi = self.phi_conv(x).reshape(b, c//2, h * w)
        g = self.g_conv(x).reshape(b, c//2, h * w).permute(0, 2, 1).contiguous()

        theta_phi = F.softmax(torch.matmul(theta, phi),dim=-1)
        theta_phi_g = torch.matmul(theta_phi, g)
        theta_phi_g = theta_phi_g.permute(0, 2, 1).contiguous().reshape(b, c//2, h, w)

        theta_phi_g = self.theta_phi_g_conv(theta_phi_g)

        output = theta_phi_g + x

        return output

    def forward(self, in_LDR, in_HDR):
        image1 = torch.cat([in_LDR[:, 0:self.c_dim, :, :], in_HDR[:, 0:self.c_dim, :, :]], 1)
        image2 = torch.cat([in_LDR[:, self.c_dim:self.c_dim * 2, :, :], in_HDR[:, self.c_dim:self.c_dim * 2, :, :]], 1)
        image3 = torch.cat([in_LDR[:, self.c_dim * 2:self.c_dim * 3, :, :], in_HDR[:, self.c_dim * 2:self.c_dim * 3, :, :]], 1)

        # if debug:
        #     print('image1: {}, image2: {}, image3: {}'.format(image1.shape, image2.shape, image3.shape))

        # encoding
        x1_32 = self.encoder_1[0](image1)
        x1_64 = self.encoder_1[1](x1_32)
        x1_128 = self.encoder_1[2](x1_64)
        x1 = self.encoder_1[3](x1_128)

        # if debug:
        #     print('x1_32: {}, x1_64: {}, x1_128: {}, x1: {}'.format(x1_32.shape, x1_64.shape, x1_128.shape, x1.shape))

        x2_32 = self.encoder_2[0](image2)
        x2_64 = self.encoder_2[1](x2_32)
        x2_128 = self.encoder_2[2](x2_64)
        x2 = self.encoder_2[3](x2_128)

        x3_32 = self.encoder_3[0](image3)
        x3_64 = self.encoder_3[1](x3_32)
        x3_128 = self.encoder_3[2](x3_64)
        x3 = self.encoder_3[3](x3_128)


        # merging
        x_cat = torch.cat([x1, x2, x3], dim=1)
        encoder_final = self.final_encoder(x_cat)

        tpl_out = self.triplepass(encoder_final, 0)
        for i in range(1,9):
            tpl_out = self.triplepass(tpl_out, i)

        glb_out = self.avgpool(encoder_final)
        glb_out = self.global_non_local(glb_out)
        required_size = [encoder_final.shape[2], encoder_final.shape[3]]
        glb_out = F.interpolate(glb_out, size=required_size)

        # decoding
        out_512 = torch.cat([tpl_out, glb_out], dim=1)
        out_128 = self.decoder1(out_512)
        out_128 = torch.cat([out_128, x1_128, x2_128, x3_128], dim=1)
        out_64 = self.decoder2(out_128)
        out_64 = torch.cat([out_64, x1_64, x2_64, x3_64], dim=1)
        out_32 = self.decoder3(out_64)
        out_32 = torch.cat([out_32, x1_32, x2_32, x3_32], dim=1)
        out = self.decoder_final(out_32)
        out = self.final(out)

        return out
