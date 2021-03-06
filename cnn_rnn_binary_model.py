import torch
import torch.nn as nn
from torch.nn import init
import torchvision.models as models
from torch.nn.utils.rnn import pack_padded_sequence
from torch.autograd import Variable
import sys

class Identity(nn.Module):
    def forward(self, x):
        return x

class EncoderCNN(nn.Module):
    def __init__(self, dtype, model_type = 'resnet'):
        """Load the trained model"""
        super(EncoderCNN, self).__init__()

        if model_type == 'densenet':
            model = models.densenet169(pretrained=True)
            self.output_size = model.classifier.in_features
            model.classifier = Identity()
        elif model_type == 'resnet':
            model = models.resnet18(pretrained=True)
            self.output_size = model.fc.in_features
            model.fc = Identity()
        else:
            print('unknown model type: %s' % (model_type))
            sys.exit(1)

        model.type(dtype)
        self.model = model
        
    def forward(self, images):
        """Extract the image feature vectors."""
        return self.model(images)
    
    
class DecoderBinaryRNN(nn.Module):
    def __init__(self, hidden_size, cnn_output_size, num_labels):
        """Set the hyper-parameters and build the layers."""
        super(DecoderBinaryRNN, self).__init__()

        self.num_labels = num_labels
        self.lstm = nn.LSTM(1, hidden_size, 1, batch_first=True)
        self.linear_img_to_lstm = nn.Linear(cnn_output_size, hidden_size)
        self.linear_final = nn.Linear(hidden_size, 1)
        self.init_weights()
    
    def init_weights(self):
        """Initialize weights."""
        nn.init.xavier_uniform(self.linear_img_to_lstm.weight)
        self.linear_img_to_lstm.bias.data.fill_(0)
        nn.init.xavier_uniform(self.linear_final.weight)
        self.linear_final.bias.data.fill_(0)
        
    def forward(self, cnn_features):
        h0 = torch.unsqueeze(self.linear_img_to_lstm(cnn_features), 0)
        c0 = torch.autograd.Variable(torch.zeros(h0.size(0), h0.size(1), h0.size(2)).cuda(), requires_grad = False)

        zero_input = torch.autograd.Variable(torch.zeros(cnn_features.size(0), self.num_labels, 1).cuda(), requires_grad = False)
        
        hiddens, _ = self.lstm(zero_input, (h0, c0))
        unbound = torch.unbind(hiddens, 1)
        combined = [self.linear_final(elem) for elem in unbound]
        combined = torch.stack(combined, 1)
        return combined
